import { Routes, Route, Navigate } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import { Layout } from '@douyinfe/semi-ui'
import LayoutHeader from './components/Header'
import LayoutSider from './components/Sidebar'
const Home = lazy(() => import('./pages/Home'))
const Knowledge = lazy(() => import('./pages/Knowledge'))
const Chat = lazy(() => import('./pages/Chat'))
const Skill = lazy(() => import('./pages/Skill'))
const Visualization = lazy(() => import('./pages/Visualization'))
const TracerouteDeepDive = lazy(() => import('./pages/Visualization/TracerouteDeepDive'))
const Settings = lazy(() => import('./pages/Settings'))
import './App.css'

function App() {
  const { Sider, Content, Header, Footer } = Layout

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <LayoutHeader />
      </Header>
      <Layout className="app-body">
        <Sider className="app-sider">
          <LayoutSider />
        </Sider>
        <Content className="app-content">
          <Suspense fallback={<div className="route-loading" role="status">正在加载页面…</div>}>
            <Routes>
              {/* Chat 为首页 */}
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="/home" element={<Home />} />
              <Route path="/knowledge/*" element={<Knowledge />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/skills" element={<Skill />} />
              <Route path="/visualization" element={<Visualization />} />
              <Route path="/visualization/traceroute" element={<TracerouteDeepDive />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Suspense>
        </Content>
      </Layout>
      <Footer className="app-footer">
        Oncall Opinion Analyse v5.0.0 © 2025
      </Footer>
    </Layout>
  )
}

export default App
