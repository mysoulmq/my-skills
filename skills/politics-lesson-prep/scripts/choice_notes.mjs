// Keep substantive changes visible to the teacher, not only in a review log.
export function choiceNotes(q) {
  const extra = (q.teachingAdditions ?? []).map(a => {
    if (![a.content, a.reason, a.basis].every(v => typeof v === 'string' && v.trim()))
      throw Error(`${q.id}: teaching addition requires content, reason and basis`);
    return `补充：${a.content}；原因：${a.reason}；依据：${a.basis}`;
  });
  const corrections = (q.review?.corrections ?? []).map(c =>
    `修正：${c.before}→${c.after}；原因：${c.reason}；依据：${c.evidence.map(e => e.locator).join('、')}`);
  return [
    ...(q.source ? [`来源：${q.source}`] : []),
    ...(q.review?.status==='source-preserved' ? [`原解析保留：${q.review.sourceNote}`] : []),
    ...(q.teachingNotes ?? []),
    ...extra, ...corrections,
    '点击1显示答案；之后按选项顺序显示纠错旁注。',
    ...q.options.map(o => `${o.key}：${o.reason}`),
  ].join('\n');
}
