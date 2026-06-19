  概述

  对A股上市公司年报中的转型风险词汇进行分析、清洗和聚类的完整流程。

  数据来源

  - 输入：/home/bo/projects/python/frequency_analyzer/output/tcfd_keywords/tcfd_keywords_summary.csv
  - 包含3大类风险词汇：
    a. 政策维度
    b. 市场维度
    c. 技术维度

  处理流程 (5个阶段)

  | 阶段    | 处理内容                                                | 输出                                           |
  |---------|---------------------------------------------------------|------------------------------------------------|
  | Phase 1 | 数据摄入：合并所有年度JSON文件                          | phase1_ingestion/merged_vocabulary.json        |
  | Phase 2 | 语义验证：使用Sentence-BERT计算相似度，过滤低相似度词汇 | phase2_validation/validation_result.json       |
  | Phase 3 | 聚类：每个类别分别用K-Means聚类，寻找最优K              | phase3_clustering/clustering_result.json       |
  | Phase 4 | 标签生成：数学标签(质心词) + 可选AI标签(LLM生成)        | 包含在聚类结果中                               |
  | Phase 5 | 组织输出：按类别组织聚类结果，生成可视化                | phase5_category_mapping/category_clusters.json |

  核心算法

  语义验证 (Phase 2)
  - 使用 shibing624/text2vec-base-chinese 模型编码词汇
  - 计算与类别锚点词的余弦相似度
  - 阈值过滤：< 0.5 的词汇被剔除

  自动聚类 (Phase 3)
  - K-Means 聚类，K范围：50-70
  - 使用轮廓系数(Silhouette Score)选择最优K
  - 每个cluster的质心最近词作为 math_label

  AI标签 (Phase 4, 可选)
  - 调用本地LLM 
  - 将cluster内所有词(最多50个)发送给LLM
  - 生成简洁的1-4字中文标签


  可能的结果

  政策维度: 68 clusters, 213 words
  市场维度: 56 clusters, 325 words
  技术维度: 57 clusters, 111 words
  ──────────────────────────────
  总计: 181 clusters, 649 words
  (从4410个原始词汇筛选)

  输出文件结构

  results/
  ├── phase1_ingestion/merged_vocabulary.json
  ├── phase2_validation/validation_result.json
  ├── phase3_clustering/clustering_result.json
  ├── phase5_category_mapping/category_clusters.json
  ├── cleaned_vocabulary.json          # 完整结果
  ├── cleaned_vocabulary_政策.png   # 可视化
  ├── cleaned_vocabulary_市场.png
  └── cleaned_vocabulary_技术.png

  技术栈

  - Sentence-BERT: shibing624/text2vec-base-chinese (语义编码)
  - sklearn: K-Means, 轮廓系数, t-SNE (聚类与可视化)
  - vLLM: 本地LLM服务 
  - matplotlib: 可视化 (配置中文字体)