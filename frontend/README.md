# Frontend - React + TypeScript智能对话界面

基于React 18、TypeScript和Ant Design 5的现代化前端应用。

## 目录结构

```
frontend/
├── src/
│   ├── api/              # API客户端
│   │   ├── index.ts      # Axios配置
│   │   ├── session.ts    # 会话API
│   │   ├── repository.ts # 文件管理API
│   │   └── request/      # 请求拦截器
│   ├── components/       # React组件
│   │   ├── Chat/        # 聊天组件
│   │   ├── Session/     # 会话管理
│   │   └── FileUpload/  # 文件上传
│   ├── pages/           # 页面组件
│   ├── hooks/           # 自定义Hooks
│   ├── store/           # 状态管理
│   ├── utils/           # 工具函数
│   ├── types/           # TypeScript类型定义
│   ├── App.tsx          # 根组件
│   └── main.tsx         # 应用入口
├── public/              # 静态资源
├── mock/                # Mock数据（开发用）
├── .env                 # 环境变量
├── package.json         # 依赖配置
├── vite.config.ts       # Vite配置
└── tsconfig.json        # TypeScript配置
```

## 技术栈

- **React 18**: 最新React特性（并发渲染、Suspense等）
- **TypeScript**: 类型安全
- **Vite**: 快速构建工具
- **Ant Design 5**: UI组件库
- **Axios**: HTTP客户端
- **React Router**: 路由管理
- **Zustand/Redux**: 状态管理（根据实际使用）

## 环境配置

### .env文件

```env
# 应用标题
VITE_TITLE=SalesPilot

# API配置
VITE_API_BASE=/api
VITE_API_PROXY=http://localhost:8080/

# 其他配置
VITE_APP_VERSION=1.0.0
```

### 环境变量使用

```typescript
// 在代码中访问
const apiBase = import.meta.env.VITE_API_BASE;
const apiProxy = import.meta.env.VITE_API_PROXY;
```

## 安装依赖

```bash
npm install
```

或使用yarn/pnpm：
```bash
yarn install
# 或
pnpm install
```

## 开发

### 启动开发服务器

```bash
npm run dev
```

应用将运行在 http://localhost:5173

### 构建生产版本

```bash
npm run build
```

构建产物在`dist/`目录

### 预览生产构建

```bash
npm run preview
```

### 代码检查

```bash
# ESLint检查
npm run lint

# 类型检查
npm run type-check
```

### 代码格式化

```bash
npm run format
```

## 核心功能

### 1. 会话管理

```typescript
import { createSession, getSessions } from '@/api/session';

// 创建新会话
const session = await createSession({ user_id: 'user123' });

// 获取会话列表
const sessions = await getSessions('user123');
```

### 2. AI对话（SSE流式）

```typescript
import { EventStreamContentType, fetchEventSource } from '@microsoft/fetch-event-source';

fetchEventSource(`${API_BASE}/ai_search/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: userInput,
    web_search: false,
    deep_research: false
  }),
  onmessage(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'text') {
      // 更新UI显示AI回复
      setMessages(prev => [...prev, { role: 'assistant', content: data.content }]);
    }
  },
  onerror(err) {
    console.error('SSE error:', err);
  }
});
```

### 3. 文件上传

```typescript
import { uploadFiles } from '@/api/repository';

const handleUpload = async (files: File[]) => {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  formData.append('user_id', userId);
  
  const result = await uploadFiles(formData);
  console.log('上传成功:', result);
};
```

## API客户端

### Axios配置

```typescript
// src/api/index.ts
import axios from 'axios';

const request = axios.create({
  baseURL: import.meta.env.VITE_API_PROXY,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
request.interceptors.request.use(
  config => {
    // 添加认证token等
    return config;
  },
  error => Promise.reject(error)
);

// 响应拦截器
request.interceptors.response.use(
  response => response.data,
  error => {
    // 统一错误处理
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export default request;
```

### API类型定义

```typescript
// src/api/session.type.d.ts
export interface Session {
  session_id: string;
  user_id: string;
  created_at: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface CreateSessionRequest {
  user_id: string;
}

export interface ChatRequest {
  message: string;
  web_search?: boolean;
  deep_research?: boolean;
  attachments?: string[];
}
```

## 组件开发

### 创建新组件

```tsx
// src/components/MyComponent/index.tsx
import React from 'react';
import { Button } from 'antd';
import styles from './index.module.scss';

interface MyComponentProps {
  title: string;
  onAction: () => void;
}

const MyComponent: React.FC<MyComponentProps> = ({ title, onAction }) => {
  return (
    <div className={styles.container}>
      <h2>{title}</h2>
      <Button type="primary" onClick={onAction}>
        执行操作
      </Button>
    </div>
  );
};

export default MyComponent;
```

### 自定义Hook

```typescript
// src/hooks/useChat.ts
import { useState, useCallback } from 'react';
import type { Message } from '@/api/session.type';

export const useChat = (sessionId: string) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = useCallback(async (content: string) => {
    setLoading(true);
    try {
      // 调用API发送消息
      // ...
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  return { messages, loading, sendMessage };
};
```

## 样式管理

### 使用Ant Design主题

```typescript
// src/App.tsx
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';

const App = () => {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 4,
        },
      }}
    >
      {/* 应用内容 */}
    </ConfigProvider>
  );
};
```

### CSS Modules

```scss
// src/components/MyComponent/index.module.scss
.container {
  padding: 20px;
  background: #fff;
  
  h2 {
    color: #333;
    margin-bottom: 16px;
  }
}
```

## 路由配置

```tsx
// src/router/index.tsx
import { createBrowserRouter } from 'react-router-dom';
import ChatPage from '@/pages/Chat';
import SessionPage from '@/pages/Session';

const router = createBrowserRouter([
  {
    path: '/',
    element: <ChatPage />,
  },
  {
    path: '/sessions',
    element: <SessionPage />,
  },
]);

export default router;
```

## 状态管理（Zustand示例）

```typescript
// src/store/chat.ts
import { create } from 'zustand';
import type { Message, Session } from '@/api/session.type';

interface ChatState {
  currentSession: Session | null;
  messages: Message[];
  setCurrentSession: (session: Session) => void;
  addMessage: (message: Message) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  currentSession: null,
  messages: [],
  setCurrentSession: (session) => set({ currentSession: session }),
  addMessage: (message) => 
    set((state) => ({ messages: [...state.messages, message] })),
}));
```

## 性能优化

### 1. 代码分割

```tsx
import { lazy, Suspense } from 'react';

const HeavyComponent = lazy(() => import('./HeavyComponent'));

function App() {
  return (
    <Suspense fallback={<div>加载中...</div>}>
      <HeavyComponent />
    </Suspense>
  );
}
```

### 2. 虚拟列表（长消息列表）

```tsx
import { List } from 'react-virtualized';

const MessageList = ({ messages }) => {
  return (
    <List
      width={600}
      height={800}
      rowCount={messages.length}
      rowHeight={80}
      rowRenderer={({ index, key, style }) => (
        <div key={key} style={style}>
          {messages[index].content}
        </div>
      )}
    />
  );
};
```

### 3. Memo优化

```tsx
import { memo } from 'react';

const MessageItem = memo(({ message }) => {
  return <div>{message.content}</div>;
}, (prev, next) => prev.message.id === next.message.id);
```

## 测试

```bash
# 运行单元测试
npm run test

# 测试覆盖率
npm run test:coverage

# E2E测试（如果配置）
npm run test:e2e
```

## 构建配置

### Vite配置优化

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'antd-vendor': ['antd'],
        },
      },
    },
  },
});
```

## 故障排查

### 1. 代理不工作
检查vite.config.ts中的proxy配置，确保target指向正确的后端地址

### 2. 类型错误
```bash
# 清除缓存重新检查
rm -rf node_modules/.vite
npm run type-check
```

### 3. 依赖冲突
```bash
rm -rf node_modules package-lock.json
npm install
```

## 部署

### Nginx配置示例

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    root /var/www/salespilot/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## 最佳实践

1. **组件拆分**: 保持组件小而专注
2. **类型安全**: 充分利用TypeScript类型系统
3. **错误边界**: 使用Error Boundary处理运行时错误
4. **可访问性**: 遵循WCAG标准
5. **性能监控**: 使用React DevTools Profiler
6. **代码规范**: 使用ESLint和Prettier

## 相关文档

- [React官方文档](https://react.dev/)
- [Vite文档](https://vitejs.dev/)
- [Ant Design文档](https://ant.design/)
- [TypeScript文档](https://www.typescriptlang.org/)
