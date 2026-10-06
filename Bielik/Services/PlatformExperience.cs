using Bielik.Core;

namespace Bielik.Services;

public static class PlatformExperience
{
#if ANDROID
    public const string ClientName = "Natywne Android";
    public const string PlatformName = "Android";
    public const string MonospaceFont = "monospace";
    public const string ConnectionHelp =
        "Emulator Android: 10.0.2.2 prowadzi do tego Maca. Na fizycznym telefonie użyj prywatnego adresu IP i HTTPS.";
#if DEBUG
    public const string InitialAddress = ModelInfo.AndroidEmulatorEndpoint;
#else
    public const string InitialAddress = "https://10.0.2.2:11434";
#endif
#else
    public const string ClientName = "Natywne iOS";
    public const string PlatformName = "iOS";
    public const string MonospaceFont = "Menlo";
    public const string ConnectionHelp =
        "Symulator iOS: 127.0.0.1 prowadzi do tego Maca. Na fizycznym iPhonie użyj prywatnego adresu IP i HTTPS.";
#if DEBUG
    public const string InitialAddress = ModelInfo.DefaultEndpoint;
#else
    public const string InitialAddress = "https://127.0.0.1:11434";
#endif
#endif
}
