一个基于[Appwrite](https://appwrite.io/)、Python3、Vue.js的服务器更新管理器

目前使用的appwrite版本为**0.12.1.201**，不同版本间可能存在兼容性问题，0.10版本可以使用[Initial commit](https://github.com/ngc7331/server-update-manager/commit/a61dd1260cbd8d036843f3d81518208f88c5154d)提交的版本。

***仅仅是个人写着玩的项目，可能存在严重的安全性问题，请谨慎使用。如果您愿意，请指教***

## 使用方法
### 在服务器上安装appwrite，请参考[官方文档](https://appwrite.io/docs/installation)
### 配置appwrite
1. 登录到appwrite
2. 创建项目，项目ID和名称任取（安全起见，ID建议使用默认的`auto-generated`，下同）。记住项目ID。进入后在`Home-Platforms`中新建Web APP，名称任填，Hostname填写前端域名（不是appwrite的域名）。
3. 在`Develop-Database-Collections`中新建Collection，ID和名称任取。记住`Collection ID`。随后在`Collection-Attributes`中添加以下项目：
    | Attribute ID | Type |
    | ------------ | ---- |
    | id | string |
    | name | string |
    | progs | string[] |
    | all_done | boolean |
    | authorized | boolean |
    | autoremove | boolean |
    | need_autoremove | boolean |
    | success | boolean |
4. 在`Develop-Users`中新建用户，ID、名称、邮箱和密码均任意设置，该邮箱和密码用于前端登录，请保证其具备一定的复杂度。记住用户ID。
5. 在`Manage-API Keys`中新建API Key，名称任取，授予以下权限。创建后点击show secret记住生成的API Key：
    - `collections.read`
    - `documents.read`
    - `documents.write`
    - `files.write`

### 配置前端
1. 将frontend文件夹的内容复制到web服务器上，在`js/app.js`中填入
```
const ENDPOINT = ""       // appwrite的API endpoint地址，类似于"https://<hostname>/v1"
const PROJECT_ID = ""     // 配置appwrite第2步设置的项目ID
const COLLECTION_ID = ""  // 配置appwrite第3步设置的Collection ID
```
2. 尝试访问

### 配置客户端
1. 将client文件夹的内容复制到需要被管理的linux系统上，将`system_update/conf-template.json`复制到`system_update/conf.json`，并填入
```
"client_name": "",        // 客户端名称，任意设置
"collection": "",         // 配置appwrite第3步设置的Collection ID
"endpoint": "",           // appwrite的API endpoint地址，类似于"https://<hostname>/v1"
"key": "",                // 配置appwrite第5步生成的API key
"permission": ["user:"],  // 在user:后面填入配置appwrite第4步设置的用户ID
"project": ""             // 配置appwrite第2步设置的项目ID
```
2. 使用pip安装依赖：`pip3 install -r requirements.txt`（其实就一个appwrite sdk）
3. 尝试运行`python3 system_update.py`