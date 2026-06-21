# AI 提取数据清洗质量报告

## 总体判断

- 决策：**NOT READY**
- 原始样本数：5
- 字段数：14
- 自动修正记录数：3
- P0 必须修正：2
- P1 强烈建议核查：6
- P2 可选优化：5

## 主要风险解释

- P0：通常表示物理上不可能、单位严重错误或关键性能越界，进入数据库或建模前必须修正。
- P1：通常表示物理上可疑、可能存在 OCR 小数点/单位错误，建议回查原文或 SI。
- P2：通常表示字段缺失、来源位置缺失或工程参数不足。

## 前 10 条高优先级核查项

- **P0** row=1, sample=, field=`BET_m2_g`：BET_m2_g = 12300 m2/g above hard maximum 10000；建议：回查原文或 SI；优先检查 OCR 小数点、单位和百分号
- **P0** row=1, sample=, field=`ICE_pct`：ICE_pct = 105 % above hard maximum 100；建议：回查原文或 SI；优先检查 OCR 小数点、单位和百分号
- **P1** row=2, sample=, field=`ID_IG`：ID_IG = 4.2  above typical range 3.5；建议：建议回查原文；优先检查单位、小数点和表格行错位
- **P1** row=2, sample=, field=`pore_volume_cm3_g`：pore_volume_cm3_g = 6.5 cm3/g above typical range 5；建议：建议回查原文；优先检查单位、小数点和表格行错位
- **P1** row=2, sample=, field=`paper_id+sample_name`：同一论文中 sample_name 重复；建议：检查是否为同一样本、不同倍率/循环数，或真实重复记录
- **P1** row=3, sample=, field=`ID_IG`：ID_IG = 4.2  above typical range 3.5；建议：建议回查原文；优先检查单位、小数点和表格行错位
- **P1** row=3, sample=, field=`pore_volume_cm3_g`：pore_volume_cm3_g = 6.5 cm3/g above typical range 5；建议：建议回查原文；优先检查单位、小数点和表格行错位
- **P1** row=3, sample=, field=`paper_id+sample_name`：同一论文中 sample_name 重复；建议：检查是否为同一样本、不同倍率/循环数，或真实重复记录
- **P2** row=2, sample=, field=`mass_loading_mg_cm2`：缺少 mass_loading_mg_cm2，影响器件级可比性；建议：回查实验方法或电极制备部分
- **P2** row=2, sample=, field=`near_duplicate_values`：关键描述符和性能值近似重复；建议：确认是否为复制残留或同一材料重复记录

## 建议下一步

1. 先处理所有 P0 项。
2. 对 P1 项回查原文表格、图注或 SI。
3. 对 P2 项补充 source_location、mass loading、电极厚度等工程信息。
4. 将清洗后的 `cleaned_database.csv` 作为综述审计或机器学习建模的输入。
