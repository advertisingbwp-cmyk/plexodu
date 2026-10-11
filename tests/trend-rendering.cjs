// Run: node tests/trend-rendering.cjs. Targeted DOM rendering, not layout tests.
const vm=require('node:vm'), fs=require('node:fs'), assert=require('node:assert/strict');
const elements=new Map();
const context={console,document:{
 addEventListener(){}, querySelectorAll(){return []},
 getElementById(id){if(!elements.has(id)) elements.set(id,{innerHTML:'',textContent:'',style:{}});return elements.get(id)},
 createElement(){return {set textContent(v){this.innerHTML=String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}}}
}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('frontend/js/tools/trend-analyzer.js','utf8'),context);
const video={rank:1,title:'A "quoted" <title>',channel:'Creator',category:'Gaming',views:300,comments:2,engagement:4,hoursAgo:3,momentumScore:42};
context.renderTrendingList([video],'');
assert(!elements.get('pulseList').innerHTML.includes('NaN'));
assert(elements.get('pulseList').innerHTML.includes('+42 idx'));
assert(elements.get('pulseList').innerHTML.includes('&quot;quoted&quot;'));
delete video.momentumScore;
context.renderTrendingList([video],'');
assert(elements.get('pulseList').innerHTML.includes('Pending'));
context.updateLowerChartWithRange=()=>{};
context.renderDeepIntelligence({keyword:'Minecraft',youtube_tags:['Minecraft'],seo_title_ideas:['Minecraft: A Guide'],sentiment:{positive_score:0.5,neutral_score:99.5},trend_intelligence:{status:'baseline',forecast:{available:false,reason:'Need history'}}});
assert(elements.get('tagsList').innerHTML.includes('Minecraft'));
assert(elements.get('aiTitlesList').innerHTML.includes('Minecraft: A Guide'));
assert(elements.get('sentimentBreakdown').innerHTML.includes('Positive: 1%'));
assert.equal(elements.get('forecastFallback').textContent,'Need history');
assert.equal(elements.get('resultsArea').style.display,'block');
console.log('PASS: momentum/missing values, attribute escaping, tags, titles, sentiment, baseline rendering');
// No repeated statuses when all windows are waiting for observations.
assert.equal((elements.get('historyTableBody').innerHTML.match(/Data collection in progress/g)||[]).length,1);
assert.equal(elements.get('forecastPanel').open,false);
context.renderDeepIntelligence({trend_intelligence:{historical_context:{'1d':{status:'available',change_pct:5}},forecast:{available:false}}});
assert(elements.get('historyTableBody').innerHTML.includes('+5%'));
assert(elements.get('historyTableBody').innerHTML.includes('Pending'));
// A single observation must not invent historical x-axis ranges or lines.
let chartConfig;
context.window={Chart:true};
context.Chart=function(ctx,config){chartConfig=config;this.destroy=()=>{}};
elements.get('viewsChart') || context.document.getElementById('viewsChart');
elements.get('viewsChart').getContext=()=>({});
context.renderLowerChart([{date:'2026-10-11 06:00',views:100}]);
assert.equal(chartConfig.data.labels.length,1);
assert(chartConfig.data.labels[0].includes('2026-10-11'));
assert.equal(chartConfig.data.datasets.length,1);
assert.equal(chartConfig.data.datasets[0].showLine,false);
console.log('PASS: consolidated history, mixed available windows, collapsed forecast, real baseline timestamp');
