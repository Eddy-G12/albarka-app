import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { MenuIcon, XIcon } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { Logo } from '../Logo';
import { NAVIGATION } from '../../config/navigation';

export function AppLayout() {
  const [tiroir, setTiroir] = useState(false);
  const { pathname } = useLocation();
  const page = NAVIGATION.find((e) => e.chemin === pathname);

  return (
    <div className="flex min-h-screen w-full bg-albarka-bg">
      <aside className="hidden w-64 shrink-0 lg:block">
        <div className="fixed inset-y-0 left-0 w-64">
          <Sidebar />
        </div>
      </aside>

      <AnimatePresence>
        {tiroir &&
        <motion.div
          className="fixed inset-0 z-40 lg:hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15, ease: [0.23, 1, 0.32, 1] }}>
          
            <div
            className="absolute inset-0 bg-albarka-black/45"
            onClick={() => setTiroir(false)}
            aria-hidden />
          
            <motion.div
            className="absolute inset-y-0 left-0 w-64"
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ duration: 0.22, ease: [0.23, 1, 0.32, 1] }}>
            
              <Sidebar onNavigation={() => setTiroir(false)} />
            </motion.div>
          </motion.div>
        }
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-albarka-border bg-white px-4 py-3 lg:hidden">
          <button
            type="button"
            aria-label={tiroir ? 'Fermer le menu' : 'Ouvrir le menu'}
            onClick={() => setTiroir((v) => !v)}
            className="rounded-md border border-albarka-border p-2 text-albarka-black">
            
            {tiroir ? <XIcon className="h-4 w-4" /> : <MenuIcon className="h-4 w-4" />}
          </button>
          <Logo taille="sm" />
          {page &&
          <span className="ml-auto truncate text-xs text-albarka-muted">{page.libelle}</span>
          }
        </header>

        <main className="albarka-scroll flex-1 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
          <Outlet />
        </main>
      </div>
    </div>);

}