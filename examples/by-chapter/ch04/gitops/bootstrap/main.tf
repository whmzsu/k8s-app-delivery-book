resource "kubernetes_namespace" "argocd" {
  metadata {
    name = "argocd"
    labels = {
      "app.kubernetes.io/name"      = "order-demo"
      "app.kubernetes.io/component" = "gitops-bootstrap"
    }
  }
}

# 用 kubectl provider 把 Argo CD 2.x 官方清单 Apply 到集群
# 清单来自 gitops/bootstrap/kustomize/argocd，由 Argo CD 自身再接管后续
resource "kubectl_manifest" "argocd_install" {
  for_each  = fileset("${path.module}/kustomize/argocd", "*.yaml")
  yaml_body = file("${path.module}/kustomize/argocd/${each.value}")
  depends_on = [kubernetes_namespace.argocd]
}
