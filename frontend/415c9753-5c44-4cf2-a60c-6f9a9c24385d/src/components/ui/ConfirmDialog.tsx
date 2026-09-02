import React, { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangleIcon } from 'lucide-react';
import { Button } from './Button';

interface ConfirmDialogProps {
  ouvert: boolean;
  titre: string;
  message: string;
  note?: string;
  libelleConfirmer?: string;
  onConfirmer: () => void;
  onAnnuler: () => void;
}

export function ConfirmDialog({
  ouvert,
  titre,
  message,
  note,
  libelleConfirmer = 'Supprimer',
  onConfirmer,
  onAnnuler
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!ouvert) return undefined;
    const gerer = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onAnnuler();
    };
    window.addEventListener('keydown', gerer);
    return () => window.removeEventListener('keydown', gerer);
  }, [ouvert, onAnnuler]);

  return (
    <AnimatePresence>
      {ouvert &&
      <motion.div
        className="fixed inset-0 z-50 flex items-center justify-center bg-albarka-black/40 px-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15, ease: [0.23, 1, 0.32, 1] }}
        onClick={onAnnuler}>
        
          <motion.div
          role="alertdialog"
          aria-modal="true"
          aria-label={titre}
          className="w-full max-w-md rounded-lg border border-albarka-border bg-white p-5 shadow-pop"
          initial={{ opacity: 0, scale: 0.96, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 8 }}
          transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
          onClick={(e) => e.stopPropagation()}>
          
            <div className="flex items-start gap-3">
              <span className="mt-0.5 rounded-full bg-[#FDF0EF] p-1.5">
                <AlertTriangleIcon className="h-4 w-4 text-[#C0392B]" aria-hidden />
              </span>
              <div>
                <h2 className="text-sm font-semibold text-albarka-black">{titre}</h2>
                <p className="mt-1 text-xs text-albarka-muted">{message}</p>
                {note &&
              <p className="mt-2 rounded border border-albarka-border bg-albarka-bg px-2.5 py-1.5 text-2xs text-albarka-muted">
                    {note}
                  </p>
              }
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button onClick={onAnnuler}>Annuler</Button>
              <Button variante="danger" onClick={onConfirmer}>
                {libelleConfirmer}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      }
    </AnimatePresence>);

}