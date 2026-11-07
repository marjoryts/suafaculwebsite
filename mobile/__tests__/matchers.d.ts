// O expo-router/testing-library registra este matcher em tempo de execução,
// mas não publica o tipo. Declaramos só o que os testes usam.
declare namespace jest {
  interface Matchers<R> {
    toHavePathname(pathname: string): R;
  }
}
