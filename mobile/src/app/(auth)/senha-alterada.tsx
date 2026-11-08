import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { Botao } from '../../components/ui/Botao';
import { TelaAuth } from '../../components/ui/TelaAuth';
import { cores, tipografia } from '../../theme/tokens';

// Figma "Senha alterada": fim da recuperação de senha (as sessões antigas foram encerradas).
export default function SenhaAlterada() {
  const router = useRouter();
  return (
    <TelaAuth variante="roxo" titulo="Senha alterada">
      <View style={styles.icone}>
        <MaterialIcons name="check-circle" size={64} color={cores.sucesso} />
      </View>
      <Text style={styles.texto}>Sua senha foi alterada com sucesso. Entre com sua nova senha.</Text>
      <Botao titulo="Entrar agora" variante="destaque" onPress={() => router.replace('/login')} />
    </TelaAuth>
  );
}

const styles = StyleSheet.create({
  icone: { alignItems: 'center' },
  texto: { ...tipografia.rotulo, color: cores.roxoEscuro, textAlign: 'center' },
});
