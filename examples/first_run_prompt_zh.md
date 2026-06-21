请使用 `ai-extracted-data-cleaner` skill 清洗 `data/extracted/AI提取数据.xlsx`。

背景：这些数据是 AI 从论文 PDF/Markdown/SI 中提取出来的样本级数据，可能存在单位错误、错列、重复样本、异常值、缺失测试条件和纸面偏差。

要求：

1. 保留原始值，不要直接覆盖或删除原始数据。
2. 将字段映射到统一字段字典。
3. 统一单位并生成 normalized columns。
4. 检查不可能值、可疑值、重复样本、同文献冲突、系统/电解液/电流密度不可比问题。
5. 用 robust z-score、IQR、leave-one-paper-out 思路标记异常值和高影响样本。
6. 输出主分析可用数据、敏感性分析数据、异常记录、二次校核清单。
7. 最终指出哪些论文/样本/字段必须回原文或 SI 二次核对。

输出到：`cleaning_outputs/<date>_ai_extracted_data_cleaning/`
