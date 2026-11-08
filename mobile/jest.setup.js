// Armazenamento seguro em memória (o módulo nativo não existe no Jest).
jest.mock('expo-secure-store', () => {
  const dados = new Map();
  return {
    getItemAsync: jest.fn(async (chave) => (dados.has(chave) ? dados.get(chave) : null)),
    setItemAsync: jest.fn(async (chave, valor) => {
      dados.set(chave, valor);
    }),
    deleteItemAsync: jest.fn(async (chave) => {
      dados.delete(chave);
    }),
    __limpar: () => dados.clear(),
    __conteudo: () => Object.fromEntries(dados),
  };
});
