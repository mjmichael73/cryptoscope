-- Promotes the container's service identity to the `service` field that the
-- platform logging libraries use everywhere else.
--
-- Two environments, one script:
--   - Compose: the compose files set the json-file `labels` log option, so
--     every log line carries the container's service name under `attrs`
--     (com.docker.compose.service locally, com.docker.swarm.service.name in
--     Swarm).
--   - Kubernetes: the kubernetes filter attaches pod metadata, and the pod
--     label `app` carries the service name.
--
-- The Modify filter cannot expand record accessors in values, so this script
-- does the lookup; missing labels leave the record untouched.
--
-- Used by deploy/fluent-bit/fluent-bit.conf (Compose) and the ConfigMap in
-- deploy/k8s/base/fluent-bit.yaml. Keep the copies in sync.

function cb_promote_service(tag, timestamp, record)
  local attrs = record["attrs"]
  if type(attrs) == "table" then
    local svc = attrs["com.docker.compose.service"]
    if svc == nil then
      svc = attrs["com.docker.swarm.service.name"]
    end
    if svc ~= nil then
      record["service"] = svc
      return 1, timestamp, record
    end
  end

  local kube = record["kubernetes"]
  if type(kube) == "table" and type(kube["labels"]) == "table" then
    local app = kube["labels"]["app"]
    if app ~= nil then
      record["service"] = app
    end
  end

  return 1, timestamp, record
end
