"""Practical release: regressions for real-data correctness and error handling."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock
import pytest
from test_phase8_trend_intelligence import DummyTrend, get_flask_module
from services.trend_intelligence import analyze_trend_intelligence, compute_historical_window_change
from services import real_api
from services.nlp_engine import analyze_sentiment


def test_refreshes_cannot_manufacture_confidence_or_forecast():
    now = datetime.now(timezone.utc)
    past = [DummyTrend(i, 1000, now - timedelta(seconds=60-i)) for i in range(40)]
    result = analyze_trend_intelligence('topic', 'YouTube', 1100, 2, {}, past, now)
    assert result['status'] == 'baseline'
    assert result['current_confidence'] == 'Low'
    assert result['velocity'] is None
    assert not result['forecast']['available']


def test_old_observation_is_not_a_one_day_baseline():
    now = datetime.now(timezone.utc)
    observations = [{'timestamp': now-timedelta(days=90), 'views': 100}, {'timestamp': now, 'views': 200}]
    assert compute_historical_window_change(observations, 200, now, 1)['status'] == 'insufficient_history'


@pytest.mark.parametrize('payload', [[1], {'keyword': 12}, {'timeframe': 'forever'}, {'region': []}])
def test_invalid_feed_inputs_return_400(payload):
    mod = get_flask_module()
    assert mod.app.test_client().post('/api/trending-feed', json=payload).status_code == 400


@pytest.mark.parametrize('status', [429, 502, 504])
def test_feed_propagates_upstream_error(status):
    mod = get_flask_module()
    with patch.object(mod, 'fetch_youtube_data', return_value={'status': status, 'error': 'Service unavailable'}):
        response = mod.app.test_client().get('/api/trending-feed?q=errors')
    assert response.status_code == status
    assert response.json['error']
    assert 'videos' not in response.json


def test_filters_and_cohorts_have_separate_history():
    mod = get_flask_module()
    raw = {'status': 200, 'title': 'Demo', 'comments': [], 'related_keywords': [],
           'daily_metrics': [{'date': '2026-10-11', 'views': 100, 'likes': 2, 'comments_count': 0, 'shares': 0}],
           'top_videos': [{'id': 'cohort-one'}]}
    keyword = 'regression-isolation'
    with mod.app.app_context():
        with patch.object(mod, 'fetch_youtube_data', return_value=raw):
            client = mod.app.test_client()
            for region in ['Pakistan', 'India']:
                assert client.post('/api/search', json={'keyword': keyword, 'region': region}).status_code == 200
            raw['top_videos'] = [{'id': 'cohort-two'}]
            assert client.post('/api/search', json={'keyword': keyword, 'region': 'Pakistan'}).status_code == 200
        rows = mod.Trend.query.filter_by(keyword=keyword).order_by(mod.Trend.trend_id.desc()).limit(3).all()
        assert len({row.observation_key for row in rows}) == 3
        assert all(row.current_confidence == 'Low' for row in rows)


@pytest.mark.parametrize('timeframe,days', [('24h', 1), ('7d', 7), ('30d', 30)])
def test_real_api_filters_aggregates_and_never_fills_empty_buckets(timeframe, days):
    captured = []
    now = datetime.now(timezone.utc)
    def get(url, **kwargs):
        params = kwargs.get('params', {})
        captured.append((url, params))
        if url == real_api.SEARCH_URL:
            return Mock(status_code=200, json=lambda: {'items': [{'id': {'videoId': 'aaa'}}, {'id': {'videoId': 'bbb'}}]})
        if url == real_api.VIDEOS_URL:
            items = [{'id': vid, 'snippet': {'title': vid, 'publishedAt': (now-timedelta(hours=3)).isoformat(), 'categoryId': '20'},
                      'statistics': {'viewCount': str(views), 'likeCount': '10', 'commentCount': '2'}} for vid, views in [('aaa', 100), ('bbb', 200)]]
            return Mock(status_code=200, json=lambda: {'items': items})
        return Mock(status_code=200, json=lambda: {'items': []})
    real_api._YT_CACHE.clear()
    with patch.object(real_api, 'get_yt_api_key', return_value='mock'), patch.object(real_api.requests, 'get', side_effect=get), patch.object(real_api, '_fetch_related_keywords', return_value=[]):
        result = real_api.fetch_youtube_data('demo', region='Global', timeframe=timeframe)
    params = next(params for url, params in captured if url == real_api.SEARCH_URL)
    cutoff = datetime.fromisoformat(params['publishedAfter'].replace('Z', '+00:00'))
    assert abs((now-cutoff).total_seconds()-days*86400) < 5
    assert 'regionCode' not in params
    assert result['daily_metrics'][0]['views'] == 300
    assert sum(point['views'] for point in result['time_series']) == 300
    assert any(point['views'] == 0 for point in result['time_series'])


def test_missing_comments_are_unavailable_not_neutral_or_positive():
    for comments in [[], ['😊😊']]:
        result = analyze_sentiment(comments)
        assert result['dominant_sentiment'] == 'unavailable'
        assert result['positive_score'] == result['neutral_score'] == 0


def test_generic_feed_has_no_unrelated_titles_and_specific_topic_is_fast():
    mod = get_flask_module()
    raw = {'status': 200, 'title': 'Test', 'comments': [], 'related_keywords': [],
           'daily_metrics': [{'date': '2026-10-11', 'views': 100, 'likes': 2, 'comments_count': 0, 'shares': 0}]}
    with patch.object(mod, 'fetch_youtube_data', return_value=raw), patch.object(mod, 'generate_context_aware_titles', side_effect=AssertionError('No AI dependency in main search')):
        client = mod.app.test_client()
        general = client.get('/api/trending-feed').json['results']['YouTube']
        assert general['seo_title_ideas'] == []
        topic = client.post('/api/search', json={'keyword': 'Minecraft'}).json['results']['YouTube']
        assert len(topic['seo_title_ideas']) == 4
        assert all('Minecraft' in title for title in topic['seo_title_ideas'])
        assert topic['youtube_tags'][0] == 'Minecraft'
        csv = client.get(f"/api/export-csv/{topic['trend_id']}")
        assert csv.status_code == 200
        assert 'Pending' in csv.text and 'BASELINE' in csv.text
        pdf = client.get(f"/api/report/{topic['trend_id']}")
        assert pdf.status_code == 200 and pdf.data.startswith(b'%PDF')


def test_pdf_keyword_is_literal_text_not_reportlab_markup():
    from services.report_generator import generate_pdf_report_buffer
    filename, content = generate_pdf_report_buffer(
        {'keyword': '<broken & topic>', 'platform': 'YouTube', 'total_views': 100},
        {'positive_score': 0, 'negative_score': 0, 'neutral_score': 0, 'dominant_sentiment': 'unavailable'},
        None, 20, 'BASELINE', 'Anonymous User')
    assert content.read(4) == b'%PDF'
    assert '<' not in filename
