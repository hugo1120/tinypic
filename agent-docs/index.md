# agent-docs 索引

## 全局约定

- 文档与任务沉淀统一放在 `agent-docs/` 下维护。
- `specs/` 存放设计文档，`plans/` 存放实施计划。
- 当前仓库优先遵循“小步重构、最小行为破坏、先验证后宣称完成”。

## 文档目录

### Specs

- `agent-docs/specs/2026-04-15-processing-refactor-phase1-design.md`
  - 主题：第一期处理链路重构设计
  - 场景：`core/processor.py` 与 `gui/main_window.py` 职责拆分、统一图像处理管线、补测试
  - 状态：已确认设计，待用户审阅文档

### Plans

- `agent-docs/plans/2026-04-15-processing-refactor-phase1-plan.md`
  - 主题：第一期处理链路重构实施计划
  - 场景：按 TDD 顺序拆分 `core` 管线、收敛兼容层、补自动化测试、调整设置保存契约
  - 状态：已完成计划编写，待选择执行方式
