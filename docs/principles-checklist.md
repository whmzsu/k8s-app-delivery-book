# 七条原则上线签字表
- [ ] 公理 1 build once / promote：三环境 image 字段相同
- [ ] 公理 2 不可变镜像 + SHA 标签：无 latest
- [ ] 公理 3 配置与镜像分离：环境差异只在 ConfigMap / overlay
- [ ] 公理 4 非 root 最小镜像：runAsNonRoot: true
- [ ] 公理 5 Git 唯一真相：生产变更来自 Git
- [ ] 公理 6 回滚方案先行：staging 有带时限的回滚演练
- [ ] 公理 7 SLO 先行于告警：最小 SLO 卡片四项填全（正式定义详见第 20 章）
