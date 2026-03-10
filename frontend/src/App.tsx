import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Itens from './pages/Itens'
import Compras from './pages/Compras'
import Estoque from './pages/Estoque'
import Lavanderia from './pages/Lavanderia'
import Quartos from './pages/Quartos'
import Auditoria from './pages/Auditoria'

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/itens" element={<Itens />} />
          <Route path="/compras" element={<Compras />} />
          <Route path="/estoque" element={<Estoque />} />
          <Route path="/lavanderia" element={<Lavanderia />} />
          <Route path="/quartos" element={<Quartos />} />
          <Route path="/auditoria" element={<Auditoria />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
