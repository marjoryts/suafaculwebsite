// Estende o app.json. O plugin do Google Sign-In só é necessário no iOS (esquema de URL
// do cliente iOS). Sem GOOGLE_IOS_URL_SCHEME ele fica de fora: no Android o login com
// Google não precisa de plugin (nem do google-services.json do Firebase).
//
// GOOGLE_IOS_URL_SCHEME = "com.googleusercontent.apps.<id>" (o "iOS URL scheme" do
// cliente OAuth iOS no Google Cloud). Não é segredo.
module.exports = ({ config }) => {
  const esquemaIos = process.env.GOOGLE_IOS_URL_SCHEME?.trim();
  if (!esquemaIos) return config;
  return {
    ...config,
    plugins: [...(config.plugins ?? []), ['@react-native-google-signin/google-signin', { iosUrlScheme: esquemaIos }]],
  };
};
