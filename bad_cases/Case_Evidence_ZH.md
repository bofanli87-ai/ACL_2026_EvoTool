# 14 道失败题逐题证据

日期：2026-10-18。固定版本 ede2328b8e54eafa6c91e8e0c8e9d42adb238c46。

所有修改均为看过测试结果后的离线诊断，不代表新模型成绩或自动修复能力。保存的 plan 与调用列表并非一一对应：Selector 可跳过子目标，原测试文件未保存逐步 subgoal 映射。

## bfcl_145 评测等价疑点

任务：Can you first calculate the greatest common divisor of the numbers 36 and 48 and then estimate the derivative of the function f(x) = x^2 at the point x = 5?

观察：GCD 的 a=36,b=48 与参考值顺序相反；数学结果相同。

待验证：不适合作为 reasoning 失败的主案例；保留原严格评分。

### 原始计划

- calculate the greatest common divisor of 36 and 48

- estimate the derivative of f(x) = x^2 at x = 5

### 原始调用

```json

[
  {
    "tool": "math_gcd",
    "args": {
      "a": 36,
      "b": 48
    },
    "status": "no_execution"
  },
  {
    "tool": "estimate_derivative",
    "args": {
      "function": "lambda x: x**2",
      "x": 5.0
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "math_gcd": {
      "a": [
        48
      ],
      "b": [
        36
      ]
    }
  },
  {
    "estimate_derivative": {
      "function": [
        "lambda x: x**2"
      ],
      "x": [
        5.0
      ],
      "dx": [
        "",
        0.001
      ],
      "method": [
        "",
        "central"
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：2 → 2 次，严格匹配 失败。

- swap_gcd_equivalent：2 → 2 次，严格匹配 通过。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。

## bfcl_44 多余调用与参数问题并存

任务：What is the average price of a 4 ft x 4 ft marble statue in the museum of Philadelphia and 6 ft x 3 ft bronze sculpture in New York museum?

观察：5 次调用而参考为 2 次；额外查 sculpture_id=0，纽约参数含 museum。

待验证：去重不足；逐项核对工具选择和实体规范化，不证明必须多模块修改。

### 原始计划

- Identify the marble statue in the museum of Philadelphia

- Identify the bronze sculpture in the New York museum

- Find the price of the marble statue

- Find the price of the bronze sculpture

- Calculate the average price of both items

### 原始调用

```json

[
  {
    "tool": "get_sculpture_details",
    "args": {
      "museum_location": "Philadelphia",
      "sculpture_id": 0
    },
    "status": "no_execution"
  },
  {
    "tool": "get_sculpture_details",
    "args": {
      "museum_location": "New York museum",
      "sculpture_id": 0
    },
    "status": "no_execution"
  },
  {
    "tool": "get_artwork_price",
    "args": {
      "museum_location": "Philadelphia",
      "sculpture_material": "marble",
      "sculpture_size": [
        4,
        4
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "get_artwork_price",
    "args": {
      "museum_location": "New York museum",
      "sculpture_material": "bronze",
      "sculpture_size": [
        6,
        3
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "get_artwork_price",
    "args": {
      "museum_location": "Philadelphia",
      "sculpture_material": "marble",
      "sculpture_size": [
        4,
        4
      ]
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "get_artwork_price": {
      "museum_location": [
        "Philadelphia"
      ],
      "sculpture_material": [
        "marble"
      ],
      "sculpture_size": [
        [
          4,
          4
        ]
      ]
    }
  },
  {
    "get_artwork_price": {
      "museum_location": [
        "New York"
      ],
      "sculpture_material": [
        "bronze"
      ],
      "sculpture_size": [
        [
          6,
          3
        ]
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：5 → 4 次，严格匹配 失败。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。

## bfcl_55 可选参数过度指定

任务：In game Battle Reign, change the armor level to 5 and find me a game guide for how to win in snowy weather conditions. Also find me any strategy guides available for game Shadow Fall.

观察：Battle Reign 的查询额外指定 type=strategy；用户只对 Shadow Fall 明确要求 strategy。

待验证：Schema 合法不保证参数符合当前子任务；验证 Caller 对可选参数的处理。

### 原始计划

- Change armor level to 5 in Battle Reign

- Find a game guide for winning in snowy weather conditions in Battle Reign

- Find strategy guides for Shadow Fall

### 原始调用

```json

[
  {
    "tool": "BattleReignGameAPI.update_player_equipment",
    "args": {
      "attribute": "armor",
      "level": 5
    },
    "status": "no_execution"
  },
  {
    "tool": "GameGuideAPI.search_guide",
    "args": {
      "game": "Battle Reign",
      "condition": "snowy weather",
      "type": "strategy"
    },
    "status": "no_execution"
  },
  {
    "tool": "GameGuideAPI.search_guide",
    "args": {
      "game": "Shadow Fall",
      "type": "strategy"
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "BattleReignGameAPI.update_player_equipment": {
      "attribute": [
        "armor"
      ],
      "level": [
        5
      ],
      "playerID": [
        123,
        ""
      ]
    }
  },
  {
    "GameGuideAPI.search_guide": {
      "game": [
        "Battle Reign"
      ],
      "condition": [
        "snowy weather"
      ],
      "type": [
        ""
      ]
    }
  },
  {
    "GameGuideAPI.search_guide": {
      "game": [
        "Shadow Fall"
      ],
      "type": [
        "strategy"
      ],
      "condition": [
        ""
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：3 → 3 次，严格匹配 失败。

- omit_unrequested_type：3 → 3 次，严格匹配 通过。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。

## bfcl_104 完全重复

任务：Can you give me 95% confidence interval for a sample mean with standard deviation of 10, sample size of 50 and sample mean of 25? And can you do the same but for a sample size of 150 instead?

观察：sample_size=50 的正确置信区间调用重复；3 次而参考为 2 次。

待验证：检查计划粒度和重复调用约束；已有正确调用。

### 原始计划

- Calculate the standard error for the first sample size

- Determine the critical t-value for the first sample size and 95% confidence level

- Compute the margin of error for the first sample size

- Calculate the confidence interval bounds for the first sample size

- Repeat the calculation process for the second sample size

### 原始调用

```json

[
  {
    "tool": "confidence_interval.calculate",
    "args": {
      "sample_std_dev": 10,
      "sample_size": 50,
      "sample_mean": 25,
      "confidence_level": 0.95
    },
    "status": "no_execution"
  },
  {
    "tool": "confidence_interval.calculate",
    "args": {
      "sample_std_dev": 10,
      "sample_size": 50,
      "sample_mean": 25,
      "confidence_level": 0.95
    },
    "status": "no_execution"
  },
  {
    "tool": "confidence_interval.calculate",
    "args": {
      "sample_std_dev": 10,
      "sample_size": 150,
      "sample_mean": 25,
      "confidence_level": 0.95
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "confidence_interval.calculate": {
      "sample_std_dev": [
        10
      ],
      "sample_size": [
        50
      ],
      "sample_mean": [
        25
      ],
      "confidence_level": [
        0.95
      ]
    }
  },
  {
    "confidence_interval.calculate": {
      "sample_std_dev": [
        10
      ],
      "sample_size": [
        150
      ],
      "sample_mean": [
        25
      ],
      "confidence_level": [
        0.95
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：3 → 2 次，严格匹配 通过。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。

## bfcl_115 查询覆盖冗余

任务：Can you find me case law details of Case No 28473 and 64725, their history and details of litigants?

观察：两个案件的历史和当事人信息被拆为 6 次查询；完整查询已经存在。

待验证：要识别参数覆盖关系，而不仅是完全重复。

### 原始计划

- Identify the case law details for Case No 28473

- Identify the case law details for Case No 64725

- Retrieve the history of Case No 28473

- Retrieve the history of Case No 64725

- Find details of litigants in Case No 28473

- Find details of litigants in Case No 64725

### 原始调用

```json

[
  {
    "tool": "law_case.get_details",
    "args": {
      "case_number": "28473",
      "include_history": true,
      "include_litigants": true
    },
    "status": "no_execution"
  },
  {
    "tool": "law_case.get_details",
    "args": {
      "case_number": "64725",
      "include_history": true,
      "include_litigants": true
    },
    "status": "no_execution"
  },
  {
    "tool": "law_case.get_details",
    "args": {
      "case_number": "28473",
      "include_history": true,
      "include_litigants": true
    },
    "status": "no_execution"
  },
  {
    "tool": "law_case.get_details",
    "args": {
      "case_number": "64725",
      "include_history": true
    },
    "status": "no_execution"
  },
  {
    "tool": "law_case.get_details",
    "args": {
      "case_number": "28473",
      "include_history": true,
      "include_litigants": true
    },
    "status": "no_execution"
  },
  {
    "tool": "law_case.get_details",
    "args": {
      "case_number": "64725",
      "include_litigants": true
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "law_case.get_details": {
      "case_number": [
        "28473"
      ],
      "include_history": [
        true
      ],
      "include_litigants": [
        true
      ]
    }
  },
  {
    "law_case.get_details": {
      "case_number": [
        "64725"
      ],
      "include_history": [
        true
      ],
      "include_litigants": [
        true
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：6 → 4 次，严格匹配 失败。

- drop_subsumed_case_queries：6 → 2 次，严格匹配 通过。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。

## bfcl_51 查询冗余与名称匹配并存

任务：Analyze the performance of the L.A Lakers in their last game and give me the field goal percentage and free throw percentage. Also, compare the team's points per game (ppg) average from 2018-2019 and 2019-2020 season.

观察：6 次调用，参考 2 次；team=L.A. Lakers 不在参考名称集合。

待验证：合并字段后仍可能因标点命名失败，需人工判断评分合理性。

### 原始计划

- Find the L.A. Lakers' last game statistics

- Extract the field goal percentage from the last game

- Extract the free throw percentage from the last game

- Find the team's points per game (ppg) average for the 2018-2019 season

- Find the team's points per game (ppg) average for the 2019-2020 season

- Compare the ppg averages between the two seasons

### 原始调用

```json

[
  {
    "tool": "sport_analysis.last_game_performance",
    "args": {
      "team": "L.A. Lakers",
      "details": [
        "field goal %",
        "free throw %"
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "sport_analysis.last_game_performance",
    "args": {
      "team": "L.A. Lakers",
      "details": [
        "field goal %"
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "sport_analysis.last_game_performance",
    "args": {
      "team": "L.A. Lakers",
      "details": [
        "free throw %"
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "sport_analysis.compare_ppg",
    "args": {
      "team": "L.A. Lakers",
      "seasons": [
        "2018-2019",
        "2019-2020"
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "sport_analysis.compare_ppg",
    "args": {
      "team": "L.A. Lakers",
      "seasons": [
        "2018-2019",
        "2019-2020"
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "sport_analysis.compare_ppg",
    "args": {
      "team": "L.A. Lakers",
      "seasons": [
        "2018-2019",
        "2019-2020"
      ]
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "sport_analysis.last_game_performance": {
      "team": [
        "L.A Lakers",
        "Los Angeles Lakers"
      ],
      "details": [
        [
          "field goal %",
          "free throw %"
        ]
      ]
    }
  },
  {
    "sport_analysis.compare_ppg": {
      "team": [
        "L.A Lakers",
        "Los Angeles Lakers"
      ],
      "seasons": [
        [
          "2018-2019",
          "2019-2020"
        ],
        [
          "18-19",
          "19-20"
        ]
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：6 → 4 次，严格匹配 失败。

- merge_details：6 → 2 次，严格匹配 失败。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。

## bfcl_149 重复并遗漏需求

任务：Find any music or theater events happening in San Diego, CA on March 1st 2023?

观察：3 次 Music 查询，缺少 Theater。

待验证：既需去重又需需求覆盖；验证携带调用参数的历史是否有帮助。

### 原始计划

- Search for events in San Diego, CA on March 1st 2023

- Filter results to include only music and theater events

- List the details of the found events

### 原始调用

```json

[
  {
    "tool": "Events_3_FindEvents",
    "args": {
      "event_type": "Music",
      "city": "San Diego, CA",
      "date": "2023-03-01"
    },
    "status": "no_execution"
  },
  {
    "tool": "Events_3_FindEvents",
    "args": {
      "event_type": "Music",
      "city": "San Diego, CA",
      "date": "2023-03-01"
    },
    "status": "no_execution"
  },
  {
    "tool": "Events_3_FindEvents",
    "args": {
      "event_type": "Music",
      "city": "San Diego, CA",
      "date": "2023-03-01"
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "Events_3_FindEvents": {
      "event_type": [
        "Music"
      ],
      "city": [
        "San Diego, CA"
      ],
      "date": [
        "2023-03-01"
      ]
    }
  },
  {
    "Events_3_FindEvents": {
      "event_type": [
        "Theater"
      ],
      "city": [
        "San Diego, CA"
      ],
      "date": [
        "2023-03-01"
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：3 → 1 次，严格匹配 失败。

- replace_one_music：3 → 3 次，严格匹配 失败。

- dedup_add_theater：3 → 2 次，严格匹配 通过。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。

## bfcl_130 可合并字段被拆开

任务：Find opening hours and ticket prices for adults and children for the National Museum in Washington D.C. and the Louvre Museum in Paris.

观察：每城市分别查询三项 details，总计 6 次；工具支持一次查询数组。

待验证：Planner 不见工具能力是候选解释；需控制提示和输入信息分别验证。

### 原始计划

- Find opening hours for the National Museum in Washington D.C.

- Find ticket prices for adults at the National Museum in Washington D.C.

- Find ticket prices for children at the National Museum in Washington D.C.

- Find opening hours for the Louvre Museum in Paris.

- Find ticket prices for adults at the Louvre Museum in Paris.

- Find ticket prices for children at the Louvre Museum in Paris.

### 原始调用

```json

[
  {
    "tool": "museum_info.get_info",
    "args": {
      "location": "Washington D.C.",
      "details": [
        "Opening hours"
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "museum_info.get_info",
    "args": {
      "location": "Washington D.C.",
      "details": [
        "Adult tickets"
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "museum_info.get_info",
    "args": {
      "location": "Washington D.C.",
      "details": [
        "Child tickets"
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "museum_info.get_info",
    "args": {
      "location": "Paris",
      "details": [
        "Opening hours"
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "museum_info.get_info",
    "args": {
      "location": "Paris",
      "details": [
        "Adult tickets"
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "museum_info.get_info",
    "args": {
      "location": "Paris",
      "details": [
        "Child tickets"
      ]
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "museum_info.get_info": {
      "location": [
        "Washington D.C.",
        "Washington DC"
      ],
      "details": [
        [
          "Opening hours",
          "Adult tickets",
          "Child tickets"
        ],
        [
          "Opening hours",
          "Child tickets",
          "Adult tickets"
        ],
        [
          "Child tickets",
          "Opening hours",
          "Adult tickets"
        ],
        [
          "Child tickets",
          "Adult tickets",
          "Opening hours"
        ],
        [
          "Adult tickets",
          "Opening hours",
          "Child tickets"
        ],
        [
          "Adult tickets",
          "Child tickets",
          "Opening hours"
        ]
      ]
    }
  },
  {
    "museum_info.get_info": {
      "location": [
        "Paris"
      ],
      "details": [
        [
          "Opening hours",
          "Adult tickets",
          "Child tickets"
        ],
        [
          "Opening hours",
          "Child tickets",
          "Adult tickets"
        ],
        [
          "Child tickets",
          "Opening hours",
          "Adult tickets"
        ],
        [
          "Child tickets",
          "Adult tickets",
          "Opening hours"
        ],
        [
          "Adult tickets",
          "Opening hours",
          "Child tickets"
        ],
        [
          "Adult tickets",
          "Child tickets",
          "Opening hours"
        ]
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：6 → 6 次，严格匹配 失败。

- merge_details：6 → 2 次，严格匹配 通过。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。

## bfcl_56 名称等价或实体绑定疑点

任务：I want a homemade healthy spaghetti recipe that is gluten free, how long will it take to prepare and cook, and what nutritional information could it provide me.

观察：recipe 名称不在允许字符串中；BFCL 没有实际 recipe_search 返回。

待验证：无法确认真实搜索结果引用关系；不要宣称执行依赖已验证。

### 原始计划

- find a gluten free homemade spaghetti recipe

- determine the preparation and cooking time of the recipe

- obtain the nutritional information of the recipe

### 原始调用

```json

[
  {
    "tool": "recipe_search",
    "args": {
      "ingredient": "spaghetti",
      "dietary_requirements": [
        "gluten_free"
      ],
      "isHomemade": true
    },
    "status": "no_execution"
  },
  {
    "tool": "recipe_prep_time",
    "args": {
      "recipe": "homemade gluten free spaghetti"
    },
    "status": "no_execution"
  },
  {
    "tool": "recipe_nutrition_info",
    "args": {
      "recipe": "homemade gluten free spaghetti"
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "recipe_search": {
      "ingredient": [
        "spaghetti"
      ],
      "dietary_requirements": [
        [
          "gluten_free"
        ]
      ],
      "isHomemade": [
        true
      ]
    }
  },
  {
    "recipe_prep_time": {
      "recipe": [
        "spaghetti",
        "homemade healthy spaghetti",
        "Homemade healthy gluten free spaghetti",
        "homemade_spaghetti"
      ]
    }
  },
  {
    "recipe_nutrition_info": {
      "recipe": [
        "homemade_spaghetti",
        "homemade healthy spaghetti",
        "spaghetti",
        "Homemade healthy gluten free spaghetti"
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：3 → 3 次，严格匹配 失败。

- recipe_name_reference_probe：3 → 3 次，严格匹配 通过。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。

## bfcl_23 重复与名称差异并存

任务：Find me the sales growth rate for company XYZ for the last 3 years and also the interest coverage ratio for the same duration.

观察：4 次调用，含 company XYZ 与 XYZ 两种 company_name。

待验证：纯去重不够；需审核名称等价和子目标冗余。

### 原始计划

- gather sales data for company XYZ over the last 3 years

- calculate the sales growth rate from the gathered data

- gather interest expense and EBIT data for company XYZ over the last 3 years

- calculate the interest coverage ratio using the gathered data

### 原始调用

```json

[
  {
    "tool": "sales_growth.calculate",
    "args": {
      "company": "XYZ",
      "years": 3
    },
    "status": "no_execution"
  },
  {
    "tool": "sales_growth.calculate",
    "args": {
      "company": "XYZ",
      "years": 3
    },
    "status": "no_execution"
  },
  {
    "tool": "financial_ratios.interest_coverage",
    "args": {
      "company_name": "company XYZ",
      "years": 3
    },
    "status": "no_execution"
  },
  {
    "tool": "financial_ratios.interest_coverage",
    "args": {
      "company_name": "XYZ",
      "years": 3
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "financial_ratios.interest_coverage": {
      "company_name": [
        "XYZ"
      ],
      "years": [
        3
      ]
    }
  },
  {
    "sales_growth.calculate": {
      "company": [
        "XYZ"
      ],
      "years": [
        3
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：4 → 3 次，严格匹配 失败。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。

## bfcl_140 重复与工具选择差异

任务：I'm looking to get updated on the following: 'significant events, news articles, and developments that since October 2021'. Please check for this verbatim. Could you provide me with the latest information on this? Include only information published after the year 2022. Also, I'd like to have "a digital painting of a masked woman with bright peacock feathers, complex and elegant, with green highlighted lines and complex patterns, reminiscent of cyberpunk Alphonse Mucha's style."

观察：搜索重复；选 generate_human_image，参考为 generate_image，参数契约不同。

待验证：两个工具说明存在语义重叠；先核对工具选择歧义，再做联合修复。

### 原始计划

- Identify significant events, news articles, and developments from October 2021 onwards

- Filter information to include only content published after 2022

- Generate a digital painting based on the described style and elements

### 原始调用

```json

[
  {
    "tool": "search_engine.query",
    "args": {
      "prompt": "significant events, news articles, and developments that since October 2021",
      "include_after_year": true
    },
    "status": "no_execution"
  },
  {
    "tool": "search_engine.query",
    "args": {
      "prompt": "significant events, news articles, and developments that since October 2021",
      "include_after_year": true
    },
    "status": "no_execution"
  },
  {
    "tool": "generate_human_image",
    "args": {
      "prompt": "a masked woman with bright peacock feathers, complex and elegant, with green highlighted lines and complex patterns, reminiscent of cyberpunk Alphonse Mucha's style",
      "image_quality": "high",
      "image_format": "PNG",
      "include_metadata": false
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "search_engine.query": {
      "prompt": [
        "significant events, news articles, and developments that since October 2021"
      ],
      "include_after_year": [
        true
      ],
      "source": [
        "",
        "Google"
      ]
    }
  },
  {
    "generate_image": {
      "prompt": [
        "a digital painting of a masked woman with bright peacock feathers, complex and elegant, with green highlighted lines and complex patterns, reminiscent of cyberpunk Alphonse Mucha's style."
      ],
      "resolution": [
        "",
        "1280x720"
      ],
      "color_mode": [
        "",
        "RGB"
      ],
      "image_quality": [
        "",
        80
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：3 → 2 次，严格匹配 失败。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。

## bfcl_58 完全重复

任务：Find hotels in Paris, France and New York, USA with at least 4 stars rating. Also I prefer hotels with amenities like free WiFi, breakfast included, and gym facility

观察：两个城市的酒店查询各重复一次；4 次而参考为 2 次。

待验证：优先案例：验证输入历史与确定性去重。

### 原始计划

- Find hotels in Paris, France with at least 4 stars rating

- Find hotels in New York, USA with at least 4 stars rating

- Filter hotels in Paris to include those with free WiFi, breakfast included, and gym facility

- Filter hotels in New York to include those with free WiFi, breakfast included, and gym facility

### 原始调用

```json

[
  {
    "tool": "hotel.find",
    "args": {
      "location": "Paris",
      "stars": 4,
      "amenities": [
        "Free WiFi",
        "Breakfast Included",
        "Gym"
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "hotel.find",
    "args": {
      "location": "New York",
      "stars": 4,
      "amenities": [
        "Free WiFi",
        "Breakfast Included",
        "Gym"
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "hotel.find",
    "args": {
      "location": "Paris",
      "stars": 4,
      "amenities": [
        "Free WiFi",
        "Breakfast Included",
        "Gym"
      ]
    },
    "status": "no_execution"
  },
  {
    "tool": "hotel.find",
    "args": {
      "location": "New York",
      "stars": 4,
      "amenities": [
        "Free WiFi",
        "Breakfast Included",
        "Gym"
      ]
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "hotel.find": {
      "location": [
        "Paris",
        "Paris, France",
        "France"
      ],
      "stars": [
        4
      ],
      "amenities": [
        [
          "Free WiFi",
          "Breakfast Included",
          "Gym"
        ]
      ]
    }
  },
  {
    "hotel.find": {
      "location": [
        "New York",
        "New York, USA",
        "NY",
        "NY, USA",
        "USA"
      ],
      "stars": [
        4
      ],
      "amenities": [
        [
          "Free WiFi",
          "Breakfast Included",
          "Gym"
        ]
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：4 → 2 次，严格匹配 通过。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。

## bfcl_71 完全重复

任务："Can you help me compare the potential energy output of two different renewable energy projects? The first project is a solar farm located at coordinates 37.7749 and -122.4194 with a total solar panel area of 50000 square feet. I would like to know the estimated energy output for the month of July. The second project is a wind farm located at coordinates 40.7128 and -74.0060 with a total of 100 wind turbines. I would also like to know the estimated energy output for this wind farm for the month of July."

观察：太阳能和风能查询各重复一次；4 次而参考为 2 次。

待验证：采集信息和计算被拆分后调用相同工具；正确调用已齐全。

### 原始计划

- gather solar farm location and panel area data

- estimate solar energy output for July

- gather wind farm location and turbine count data

- estimate wind energy output for July

- compare the estimated energy outputs of both projects

### 原始调用

```json

[
  {
    "tool": "solarFarm.potential",
    "args": {
      "coordinates": [
        37.7749,
        -122.4194
      ],
      "panelArea": 50000,
      "month": "July"
    },
    "status": "no_execution"
  },
  {
    "tool": "solarFarm.potential",
    "args": {
      "coordinates": [
        37.7749,
        -122.4194
      ],
      "panelArea": 50000,
      "month": "July"
    },
    "status": "no_execution"
  },
  {
    "tool": "windFarm.potential",
    "args": {
      "coordinates": [
        40.7128,
        -74.006
      ],
      "turbineCount": 100,
      "month": "July"
    },
    "status": "no_execution"
  },
  {
    "tool": "windFarm.potential",
    "args": {
      "coordinates": [
        40.7128,
        -74.006
      ],
      "turbineCount": 100,
      "month": "July"
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "solarFarm.potential": {
      "coordinates": [
        [
          37.7749,
          -122.4194
        ]
      ],
      "panelArea": [
        50000.0
      ],
      "month": [
        "July"
      ]
    }
  },
  {
    "windFarm.potential": {
      "coordinates": [
        [
          40.7128,
          -74.006
        ]
      ],
      "turbineCount": [
        100.0
      ],
      "month": [
        "July"
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：4 → 2 次，严格匹配 通过。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。

## bfcl_29 重复与可选参数并存

任务：Find the conviction status of a criminal with name John Doe in New York, also find the nature of the criminal offenses he committed.

观察：状态查询重复；optional_param=true 不被参考接受。

待验证：分别移除重复和可选参数均不足，联合修改可检验多错误共存。

### 原始计划

- Find the criminal record of John Doe in New York

- Determine the conviction status of John Doe

- Identify the nature of the criminal offenses committed by John Doe

### 原始调用

```json

[
  {
    "tool": "criminal_record.get_status",
    "args": {
      "criminal_name": "John Doe",
      "region": "New York"
    },
    "status": "no_execution"
  },
  {
    "tool": "criminal_record.get_status",
    "args": {
      "criminal_name": "John Doe",
      "region": "New York"
    },
    "status": "no_execution"
  },
  {
    "tool": "criminal_record.get_offense_nature",
    "args": {
      "criminal_name": "John Doe",
      "optional_param": true
    },
    "status": "no_execution"
  }
]

```

### 标准调用

```json

[
  {
    "criminal_record.get_status": {
      "criminal_name": [
        "John Doe"
      ],
      "region": [
        "New York",
        "NY"
      ]
    }
  },
  {
    "criminal_record.get_offense_nature": {
      "criminal_name": [
        "John Doe"
      ],
      "optional_param": [
        "",
        false
      ]
    }
  }
]

```

### 离线修改结果

- exact_dedup：3 → 2 次，严格匹配 失败。

- omit_optional：3 → 3 次，严格匹配 失败。

- dedup_and_omit_optional：3 → 2 次，严格匹配 通过。

完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。
