{{- define "order-demo-common.labels" -}}
app.kubernetes.io/name: order-demo
app.kubernetes.io/managed-by: {{ .Values.managedBy }}
{{- end -}}
{{- define "order-demo-common.securityContext" -}}
runAsNonRoot: true
seccompProfile:
  type: RuntimeDefault
{{- end -}}
