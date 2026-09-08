const DENY_LEVEL = 10;
const body = $input.first().json.body;
if (!body?.student || !Array.isArray(body.alerts)) {
  throw new Error("student and alerts are required");
}
return body.alerts.map((alert) => {
  const level = Number(alert.level);
  if (!Number.isFinite(level) || !alert.ip || !alert.rule) {
    throw new Error("Each alert needs level, ip and rule");
  }
  const severity = level >= 10 ? "High" : level >= 7 ? "Medium" : "Low";
  const decision = level >= DENY_LEVEL ? "deny" : "allow";
  return { json: {
    student: body.student, src_ip: alert.ip, level,
    rule: String(alert.rule), fail_count: Number(alert.fail_count ?? 0),
    severity, decision,
    reason: `level ${level} (rule ${alert.rule}), 기준 ${DENY_LEVEL} → ${decision}`
  }};
});
