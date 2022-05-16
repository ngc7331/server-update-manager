一个基于[Appwrite](https://appwrite.io/)、Python3、Vue.js的服务器更新管理器

目前使用的appwrite版本为**0.13.4.304**，不同版本间可能存在兼容性问题，0.10版本可以使用[Initial commit](https://github.com/ngc7331/server-update-manager/commit/a61dd1260cbd8d036843f3d81518208f88c5154d)提交的版本。

***仅仅是个人写着玩的项目，可能存在严重的安全性问题，请谨慎使用。如果您愿意，请指教***

## 工作模式
```
----------client---------                      ---backend---
| 1.通过apt获取更新信息  |        2.Post        |           |
|                       | -------------------> |           |
|      3.等待授权       | 4.每隔一段时间进行查询 |           |
|                       | <------------------> |           |
|    5.授权，执行更新    |                      |           |
|  并获取autoremove信息  |       6.Post         |           |
|                       | -------------------> |           |
|      7.等待授权       | 8.每隔一段时间进行查询 |           |
|                       | <------------------> |           |
| 9.授权，执行autoremove |                      |           |
-------------------------                      |           |
                                               |           |
                                               |           |
-----frontend-----                             |           |
| 1.通过邮箱和密码 |                            |           |
| 或sessionID登录 |       2.获取Session         |           |
|                 | <------------------------> |           |
|                 |     3.获取client信息        |           |
|                 | <------------------------> |           |
| 4.显示client信息 |                            |           |
| 5.用户修改(授权) |         6.提交改动          |           |
|                 | -------------------------> |           |
-------------------                            -------------
```
### 状态
| 状态码 | 解释 |
| ----- | --- |
| -1 | 致命错误导致程序退出 |
| | |
| 0 | 程序初始化，等待apt update |
| 1 | 已授权，等待apt hold |
| 2 | 已授权，等待apt upgrade |
| 3 | 已授权，等待apt autoremove |
| 5 | 全部完成 |
| 9 | 未发现可用升级 |
| | |
| 10 | 正在执行apt update |
| 11 | 正在设置apt hold |
| 12 | 正在执行apt upgrade |
| 13 | 正在执行apt autoremove |
| | |
| 22 | 等待apt upgrade授权 |
| 23 | 等待apt autoremove授权 |

## 使用方法
### 在服务器上安装appwrite，请参考[官方文档](https://appwrite.io/docs/installation)
### 配置appwrite
1. 登录到appwrite
2. 创建项目，项目ID和名称任取（安全起见，ID建议使用默认的`auto-generated`，下同）。记住项目ID。进入后在`Home-Platforms`中新建Web APP，名称任填，Hostname填写前端域名（不是appwrite的域名）。
3. 在`Develop-Database-Collections`中新建Collection，ID和名称任取。记住`Collection ID`。随后在`Collection-Attributes`中添加以下项目：
    | Attribute ID | Type |
    | ------------ | ---- |
    | status | integer |
    | error | bool |
    | name | string |
    | time | string |
    | msg | string |
    | progs | string[] |
    | log | string(url) |
4. 在`Develop-Users`中新建用户，ID、名称、邮箱和密码均任意设置，该邮箱和密码用于前端登录，请保证其具备一定的复杂度。记住用户ID。
5. 在`Storage`中新建Bucket，ID、名称任意
6. 在`Manage-API Keys`中新建API Key，名称任取，授予以下权限。创建后点击show secret记住生成的API Key：
    - `collections.read`
    - `documents.read`
    - `documents.write`
    - `files.read`
    - `files.write`

### 配置前端
1. 将frontend文件夹的内容复制到web服务器上，将`js/conf-template.js`复制到`js/conf.js`，并填入
```
export const ENDPOINT = ""       // appwrite的API endpoint地址，类似于"https://<hostname>/v1"
export const PROJECT_ID = ""     // 配置appwrite第2步设置的项目ID
export const COLLECTION_ID = ""  // 配置appwrite第3步设置的Collection ID
```
2. 尝试访问

### 配置客户端
1. 将client文件夹的内容复制到需要被管理的linux系统上，将`system_update/conf-template.json`复制到`system_update/conf.json`，并填入
```
"bucket": "",             // 配置appwrite第5步设置的Bucket ID
"client_name": "",        // 客户端名称，任意设置
"collection": "",         // 配置appwrite第3步设置的Collection ID
"endpoint": "",           // appwrite的API endpoint地址，类似于"https://<hostname>/v1"
"key": "",                // 配置appwrite第6步生成的API key
"permission": ["user:"],  // 在user:后面填入配置appwrite第4步设置的用户ID
"project": ""             // 配置appwrite第2步设置的项目ID
```
2. 使用pip安装依赖：`pip3 install -r requirements.txt`（其实就一个appwrite sdk）
3. 尝试运行`python3 system_update.py`

## Changelog
- 2022.05.16 部分代码重构，更新appwrite至**0.13.4.304**
- 2022.02.20 更新client初始化逻辑，加入锁机制
- 2022.02.10 修改状态表示，优化错误处理
- 2022.02.06 增加更多状态提示，前端使用import避免覆盖`js/app.js`后需要重复填入id的问题，修复错误
- 2022.02.04 增加更新完成后的日志文件显示
- 2022.02.02 将状态整合到一个integer变量中，小改前端样式