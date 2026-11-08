import { Alert } from 'react-native';

/** Pede confirmação antes de uma ação destrutiva ou demorada (como o confirm() do painel Web). */
export function confirmar(titulo: string, mensagem: string, acao: () => void, rotulo = 'Excluir') {
  Alert.alert(titulo, mensagem, [
    { text: 'Cancelar', style: 'cancel' },
    { text: rotulo, style: 'destructive', onPress: acao },
  ]);
}
