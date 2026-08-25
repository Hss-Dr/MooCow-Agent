import './index.scss'
import { Nav } from './nav'

export function BaseLayout({ children }: { children?: React.ReactNode }) {
  return (
    <div className="base-layout">
      <main>
        <div className="base-layout__sidebar">
          <div className="base-layout__sidebar-main scrollbar-style">
            <div className="base-layout__sidebar-main-content">
              <Nav />
            </div>
          </div>
        </div>

        <div className="base-layout__content">{children}</div>
      </main>
    </div>
  )
}
