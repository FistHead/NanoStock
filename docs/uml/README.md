# UML-диаграммы проекта «Мипл»

Файлы `.puml` — для [PlantUML](https://www.plantuml.com/plantuml/uml/) (онлайн или плагин в IDE).  
Вставь в диплом как **Приложение А** (экспорт в PNG/SVG).

| Файл | Диаграмма |
|------|-----------|
| `01_use_case.puml` | Варианты использования (что делает пользователь) |
| `02_components.puml` | Компоненты системы |
| `03_classes.puml` | Классы ядра и движка |
| `04_sequence_step.puml` | Последовательность одного шага симуляции |

## Как получить картинку

1. Открой https://www.plantuml.com/plantuml/uml/
2. Скопируй содержимое `.puml` → Submit
3. Сохрани PNG → в Word «Вставка → Рисунок»

Или в VS Code: расширение **PlantUML** → `Alt+D` предпросмотр.

---

## Mermaid (для просмотра в Cursor / GitHub)

### Варианты использования (упрощённо)

```mermaid
flowchart LR
  U((Пользователь))
  U --> A[О проекте]
  U --> B[Симуляции]
  B --> B1[Создать / удалить / переименовать]
  B --> B2[Авто-симуляция]
  B --> B3[Акции и миплы]
  B --> C[Окно симуляции]
  C --> C1[Шаг / авто-прогон]
  C --> C2[График свечей]
  C --> C3[Чат / решения / активы]
  C --> C4[Профиль мипла]
```

### Компоненты

```mermaid
flowchart TB
  subgraph client [Браузер]
    UI[HTML CSS JS]
  end
  subgraph web [WebSite]
    Flask[app.py]
    Eng[engine.py]
    Br[brains.py]
  end
  subgraph core [Ядро]
    Core[Core.py OrderBook Stock]
  end
  subgraph ml [Модели]
    NN[mrplip_17M_3]
    Gr[AffectorSeller]
  end
  UI --> Flask
  Flask --> Eng
  Eng --> Core
  Eng --> Br
  Br --> NN
  Br --> Gr
```

### Шаг симуляции

```mermaid
sequenceDiagram
  actor U as Пользователь
  participant W as sim.js
  participant F as Flask
  participant S as Simulation
  participant B as brains
  participant C as Core

  U->>W: Шаг
  W->>F: POST /step
  F->>S: step()
  S->>S: событие / дрифт
  loop миплы
    S->>B: predict()
    B-->>S: решение + текст
    S->>C: сделка / стакан
  end
  S->>C: flush()
  S-->>F: snapshot
  F-->>W: JSON
  W-->>U: UI
```
