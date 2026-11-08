import { Image } from 'react-native';

import { dimensoes } from '../../theme/tokens';

const IMAGENS = {
  roxo: require('../../../assets/figma/logo-roxo.png'),
  branco: require('../../../assets/figma/logo-branco.png'),
};

// Logo "SuaFacul" exportada do Figma (128×110 no topo das telas de login/cadastro).
export function Logo({ cor = 'roxo', grande }: { cor?: keyof typeof IMAGENS; grande?: boolean }) {
  const { largura, altura } = grande ? dimensoes.logoGrande : dimensoes.logo;
  return (
    <Image
      source={IMAGENS[cor]}
      style={{ width: largura, height: altura }}
      resizeMode="contain"
      accessibilityRole="image"
      accessibilityLabel="SuaFacul"
    />
  );
}
