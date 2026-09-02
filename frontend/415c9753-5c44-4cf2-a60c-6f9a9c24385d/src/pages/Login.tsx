import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { LockIcon } from 'lucide-react';
import { Logo } from '../components/Logo';
import { Button } from '../components/ui/Button';
import { Champ, Input } from '../components/ui/Field';
import { useAuth } from '../contexts/AuthContext';

export function Login() {
  const { seConnecter } = useAuth();
  const [username, setUsername] = useState('');
  const [motDePasse, setMotDePasse] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(false);

  const soumettre = async (e: React.FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setChargement(true);
    try {
      await seConnecter(username, motDePasse);
    } catch (exception) {
      setErreur(
        exception instanceof Error ? exception.message : 'Connexion impossible pour le moment.'
      );
    } finally {
      setChargement(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-albarka-black px-4 py-10">
      <motion.div
        initial={{ opacity: 0, y: 12, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.28, ease: [0.23, 1, 0.32, 1] }}
        className="w-full max-w-sm">
        
        <div className="mb-6 flex justify-center">
          <Logo taille="lg" sombre />
        </div>

        <form
          onSubmit={soumettre}
          className="rounded-lg border border-albarka-border bg-white p-6 shadow-pop">
          
          <h1 className="text-base font-semibold text-albarka-black">Connexion</h1>
          <p className="mt-1 text-xs text-albarka-muted">
            Accès réservé aux équipes ALBARKA. Vos droits déterminent les modules visibles.
          </p>

          <div className="mt-5 space-y-4">
            <Champ label="Identifiant" htmlFor="username">
              <Input
                id="username"
                value={username}
                autoComplete="username"
                onChange={(e) => setUsername(e.target.value)}
                placeholder="giovanni"
                required />
              
            </Champ>
            <Champ label="Mot de passe" htmlFor="password">
              <Input
                id="password"
                type="password"
                value={motDePasse}
                autoComplete="current-password"
                onChange={(e) => setMotDePasse(e.target.value)}
                placeholder="••••••••"
                required />
              
            </Champ>
          </div>

          {erreur &&
          <p
            role="alert"
            className="mt-4 rounded-md border border-[#F0C8C4] bg-[#FDF3F2] px-3 py-2 text-xs text-[#8E2B22]">
            
              {erreur}
            </p>
          }

          <Button
            type="submit"
            variante="primaire"
            chargement={chargement}
            className="mt-5 w-full"
            icone={<LockIcon className="h-4 w-4" />}>
            
            Se connecter
          </Button>

          <p className="mt-4 text-center text-2xs text-albarka-muted">
            Maquette : giovanni / sadmin123 · theo / admin123 · parfait / parfait123
          </p>
        </form>
      </motion.div>
    </div>);

}