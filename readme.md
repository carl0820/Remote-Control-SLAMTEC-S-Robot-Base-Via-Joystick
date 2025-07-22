USB适配器的无线wifi2.4G 手柄，通过开发一个桌面的Python应用程序来遥控机器人前进后退左转盒右转。
机器人的IP：10.160.128.227  端口1448
机器人的控制API为：
前进：
/api/core/motion/v1/actions
{
    "action_name": "slamtec.agent.actions.MoveByAction",
    "options": {
        "direction": 0,
        "duration": 500
    }
}
后退：
{
    "action_name": "slamtec.agent.actions.MoveByAction",
    "options": {
        "direction": 1,
        "duration": 500
    }
}
左转：
/api/core/motion/v1/actions
{
    "action_name": "slamtec.agent.actions.MoveByAction",
    "options": {
        "direction": 2,
        "duration": 500
    }
}
右转：
{
    "action_name": "slamtec.agent.actions.MoveByAction",
    "options": {
        "direction": 3,
        "duration": 500
    }
}

---

## 7-22 新增功能

### 按钮8：机器人回桩
按下手柄按钮8时，调用机器人回桩接口：

- `POST /api/multi-floor/motion/v1/gohomeaction`
- 请求体：
  ```json
  {
  }
  ```
- 响应示例：
  ```json
  {
    "action_id": 22,
    "action_name": "slamtec.agent.actions.MultiFloorBackHomeAction",
    "stage": "INITIALIZING",
    "state": {
        "reason": "",
        "result": 0,
        "status": 0
    }
  }
  ```

### 按钮6：创建POI点
按下手柄按钮6时，调用当前点创建POI接口，起始点为P001，每调用一次进行递增显示：

- `POST /api/core/artifact/v1/pois` - 创建当前点POI
- 响应体示例：
  ```json
  {
    "id": "e77857db-673d-4b13-aae6-fc089eb24bce",
    "metadata": {
      "display_name": "P001"
    }
  }
  ```
- 响应：true

### 按钮7：终止当前行为
按下手柄按钮7时，调用终止当前行为的接口
/api/core/motion/v1/actions/:current