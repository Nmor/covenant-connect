{{- define "covenant-connect.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "covenant-connect.fullname" -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "covenant-connect.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
app.kubernetes.io/name: {{ include "covenant-connect.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "covenant-connect.selectorLabels" -}}
app.kubernetes.io/name: {{ include "covenant-connect.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "covenant-connect.backendName" -}}
{{ include "covenant-connect.fullname" . }}-backend
{{- end -}}

{{- define "covenant-connect.frontendName" -}}
{{ include "covenant-connect.fullname" . }}-frontend
{{- end -}}

{{- define "covenant-connect.redisName" -}}
{{ include "covenant-connect.fullname" . }}-redis
{{- end -}}

{{- define "covenant-connect.postgresName" -}}
{{ include "covenant-connect.fullname" . }}-postgres
{{- end -}}

{{- define "covenant-connect.backendSecretName" -}}
{{ include "covenant-connect.fullname" . }}-backend-env
{{- end -}}

{{- define "covenant-connect.postgresSecretName" -}}
{{ include "covenant-connect.fullname" . }}-postgres
{{- end -}}

{{- define "covenant-connect.redisSecretName" -}}
{{ include "covenant-connect.fullname" . }}-redis-auth
{{- end -}}
