export function incumbent(values){
  let best=null;
  return values.map(value=>{if(value!==null)best=best===null?value:Math.min(best,value);return best;});
}
export function pathSeries(evidence,objective,mode='candidate'){
  if(!Object.hasOwn(evidence.reference_minima,objective))throw Error('Unknown objective');
  if(!['candidate','incumbent'].includes(mode))throw Error('Unknown path mode');
  const reference=evidence.reference_minima[objective];
  return evidence.paths.filter(row=>row.objective===objective).map(row=>{
    const values=mode==='incumbent'?incumbent(row.losses):[...row.losses];
    return {...row,raw:[...row.losses],values,gaps:values.map(value=>value===null?null:value-reference),carried:values.map((value,i)=>value!==null&&row.losses[i]===null)};
  });
}
export function accountingContrast(rows,weight){
  if(!Number.isFinite(weight)||weight<0||weight>.2||rows.length!==2)throw Error('Invalid archived contrast');
  const [reference,hand]=rows;
  const scores=rows.map(row=>-row.utility+weight*row.collected);
  return {scores,delta:scores[1]-scores[0],collectedDelta:hand.collected-reference.collected,unpaidDelta:hand.unpaid-reference.unpaid,requestedDelta:hand.requested-reference.requested};
}
