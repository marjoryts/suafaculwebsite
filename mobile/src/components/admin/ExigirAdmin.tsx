import { ReactNode } from 'react';

import { useSessao } from '../../auth/SessaoProvider';
import { EstadoVazio } from '../ui/Estados';
import { Tela } from '../ui/Tela';

// Esconde o painel de quem não é admin. É só conforto de interface: quem barra de
// verdade é o servidor (toda rota /admin/* confere o papel no banco e responde 403).
export function ExigirAdmin({ titulo, children }: { titulo: string; children: ReactNode }) {
  const { usuario } = useSessao();
  if (usuario?.tipo !== 'admin') {
    return (
      <Tela cabecalho={{ titulo }}>
        <EstadoVazio icone="lock" titulo="Acesso restrito" mensagem="Esta área é exclusiva para administradores." />
      </Tela>
    );
  }
  return <>{children}</>;
}
