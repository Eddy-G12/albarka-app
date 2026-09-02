import React from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { FiltresProvider } from './contexts/FiltresContext';
import { AppLayout } from './components/layout/AppLayout';
import { pageAutorisee } from './config/navigation';
import { Login } from './pages/Login';
import { Accueil } from './pages/Accueil';
import { DashboardGlobal } from './pages/DashboardGlobal';
import { MonDashboard } from './pages/MonDashboard';
import { CashFlow } from './pages/CashFlow';
import { DashboardQr } from './pages/DashboardQr';
import { EtudeComparative } from './pages/EtudeComparative';
import { ApproDestockage } from './pages/ApproDestockage';
import { ComparaisonsMoM } from './pages/ComparaisonsMoM';
import { Reactivite } from './pages/Reactivite';
import { Transactions } from './pages/Transactions';
import { SuiviQrCode } from './pages/SuiviQrCode';
import { Portefeuilles } from './pages/Portefeuilles';
import { MomoApp } from './pages/MomoApp';
import { SuiviPersonnes } from './pages/SuiviPersonnes';
import { Historique } from './pages/Historique';
import { Administration } from './pages/Administration';

function RouteProtegee({ children }: {children: React.ReactNode;}) {
  const { utilisateur } = useAuth();
  const { pathname } = useLocation();
  if (!utilisateur) return <Navigate to="/connexion" replace />;
  if (!pageAutorisee(pathname, utilisateur.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function Routage() {
  const { connecte } = useAuth();

  if (!connecte) {
    return (
      <Routes>
        <Route path="*" element={<Login />} />
      </Routes>);

  }

  const protegee = (element: React.ReactNode) => <RouteProtegee>{element}</RouteProtegee>;

  return (
    <Routes>
      <Route path="/connexion" element={<Navigate to="/" replace />} />
      <Route element={<AppLayout />}>
        <Route path="/" element={<Accueil />} />
        <Route path="/dashboard" element={protegee(<DashboardGlobal />)} />
        <Route path="/mon-dashboard" element={protegee(<MonDashboard />)} />
        <Route path="/cash-flow" element={protegee(<CashFlow />)} />
        <Route path="/dashboard-qr" element={protegee(<DashboardQr />)} />
        <Route path="/etude-comparative" element={protegee(<EtudeComparative />)} />
        <Route path="/appro" element={protegee(<ApproDestockage />)} />
        <Route path="/mom" element={protegee(<ComparaisonsMoM />)} />
        <Route path="/reactivite" element={protegee(<Reactivite />)} />
        <Route path="/transactions" element={protegee(<Transactions />)} />
        <Route path="/suivi-qr" element={protegee(<SuiviQrCode />)} />
        <Route path="/portefeuilles" element={protegee(<Portefeuilles />)} />
        <Route path="/momo-app" element={protegee(<MomoApp />)} />
        <Route path="/suivi-personnes" element={protegee(<SuiviPersonnes />)} />
        <Route path="/historique" element={protegee(<Historique />)} />
        <Route path="/administration" element={protegee(<Administration />)} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>);

}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <FiltresProvider>
          <Routage />
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                borderRadius: '6px',
                border: '1px solid #E9ECEF',
                fontSize: '13px'
              }
            }} />
          
        </FiltresProvider>
      </AuthProvider>
    </BrowserRouter>);

}