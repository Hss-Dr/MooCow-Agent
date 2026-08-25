import { BaseLayout } from '@/layout/base'
import NotFound from '@/pages/404'
import Chat from '@/pages/chat'
import Index from '@/pages/index'
import Login from '@/pages/login'
import Repository from '@/pages/repository'
import {
  Outlet,
  RouteObject,
  createBrowserRouter,
  useLocation,
  Navigate,
} from 'react-router-dom'
import { userState } from '@/store/user'

// 路由保护组件
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const hasToken = !!userState.token

  if (!hasToken) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

export type IRouteObject = {
  children?: IRouteObject[]
  name?: string
  auth?: boolean
  pure?: boolean
  meta?: any
} & Omit<RouteObject, 'children'>

export const routes: IRouteObject[] = [
  {
    path: '/',
    Component: Index,
    auth: true,
  },
  {
    path: '/chat/:id',
    Component: Chat,
    auth: true,
  },
  {
    path: '/repository',
    Component: Repository,
    auth: true,
  },
]

function Layout() {
  const location = useLocation()
  return (
    <BaseLayout>
      <Outlet key={location.pathname} />
    </BaseLayout>
  )
}

export const router = createBrowserRouter(
  [
    {
      path: '/login',
      Component: Login,
    },
    helper({
      path: '/',
      element: (
        <ProtectedRoute>
          <Layout />
        </ProtectedRoute>
      ),
      children: routes.filter((r) => r.auth !== false),
    }),
    helper({
      path: '404',
      Component: NotFound,
      pure: true,
    }),
    helper({
      path: '*',
      Component: NotFound,
    }),
  ],
  {
    basename: import.meta.env.BASE_URL,
  },
)

function helper(route: IRouteObject) {
  const _route = {
    ...route,
  }

  if (_route.children) {
    _route.children = _route.children.map((child: any) => helper(child))
  }

  if (_route.auth === undefined) {
    _route.auth = true
  }

  return _route as RouteObject
}
