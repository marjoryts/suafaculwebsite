import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { chaveDia, DIAS_CURTOS, semana } from '../../catalogo/datas';
import { cores, dimensoes, espaco, familias, raio, tipografia } from '../../theme/tokens';

type Props = {
  referencia: Date; // qualquer dia da semana exibida
  hoje: Date;
  selecionado: string | null; // chave "AAAA-MM-DD"
  /** Dias com prova (chave "AAAA-MM-DD") ganham um ponto. */
  marcados: Set<string>;
  onSelecionar: (chave: string | null) => void;
  onMudarSemana: (delta: -1 | 1) => void;
};

const MESES_CURTOS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

// Faixa da semana do Figma "Vestibulares": Seg–Dom com o dia em destaque em laranja.
export function SemanaCalendario({ referencia, hoje, selecionado, marcados, onSelecionar, onMudarSemana }: Props) {
  const dias = semana(referencia);
  const chaveHoje = chaveDia(hoje);
  const intervalo = `${dias[0].getDate()} ${MESES_CURTOS[dias[0].getMonth()]} – ${dias[6].getDate()} ${MESES_CURTOS[dias[6].getMonth()]}`;

  return (
    <View style={styles.caixa}>
      <View style={styles.topo}>
        <Pressable accessibilityRole="button" accessibilityLabel="Semana anterior" onPress={() => onMudarSemana(-1)} hitSlop={espaco.sm}>
          <MaterialIcons name="chevron-left" size={28} color={cores.roxoEscuro} />
        </Pressable>
        <Text style={styles.intervalo}>{intervalo}</Text>
        <Pressable accessibilityRole="button" accessibilityLabel="Próxima semana" onPress={() => onMudarSemana(1)} hitSlop={espaco.sm}>
          <MaterialIcons name="chevron-right" size={28} color={cores.roxoEscuro} />
        </Pressable>
      </View>
      <View style={styles.linha}>
        {dias.map((d, i) => {
          const chave = chaveDia(d);
          const ativo = chave === selecionado;
          const temProva = marcados.has(chave);
          return (
            <Pressable
              key={chave}
              accessibilityRole="button"
              accessibilityLabel={`${DIAS_CURTOS[i]} ${d.getDate()}${temProva ? ', tem prova' : ''}${chave === chaveHoje ? ', hoje' : ''}`}
              accessibilityState={{ selected: ativo }}
              onPress={() => onSelecionar(ativo ? null : chave)}
              style={styles.coluna}
            >
              <Text style={styles.diaSemana}>{DIAS_CURTOS[i]}</Text>
              <View style={[styles.dia, ativo && styles.diaAtivo, !ativo && chave === chaveHoje && styles.diaHoje]}>
                <Text style={[styles.numero, ativo && styles.numeroAtivo]}>{d.getDate()}</Text>
              </View>
              <View style={[styles.ponto, temProva && styles.pontoAtivo]} />
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  caixa: { gap: espaco.sm },
  topo: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  intervalo: { ...tipografia.legenda, fontSize: 14, color: cores.roxoEscuro },
  linha: { flexDirection: 'row', justifyContent: 'space-between' },
  coluna: { alignItems: 'center', gap: espaco.xs, minWidth: dimensoes.areaToque },
  diaSemana: { ...tipografia.legenda, fontSize: 14, color: cores.textoSuave },
  // Círculos do Figma (50×50); aqui 44 para caber 7 em telas estreitas.
  dia: { width: 44, height: 44, borderRadius: raio.pilula, alignItems: 'center', justifyContent: 'center' },
  diaAtivo: { backgroundColor: cores.laranja },
  diaHoje: { borderWidth: 1.5, borderColor: cores.laranja },
  numero: { fontFamily: familias.interSemi, fontSize: 18, color: cores.texto },
  numeroAtivo: { color: cores.branco },
  ponto: { width: 6, height: 6, borderRadius: 3 },
  pontoAtivo: { backgroundColor: cores.roxo },
});
