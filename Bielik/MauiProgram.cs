using Bielik.Core;
using Bielik.Services;
using Bielik.ViewModels;
using Bielik.Views;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.AI;
#if DEBUG
using System.Globalization;
using Microsoft.Maui.DevFlow.Agent;
#endif

namespace Bielik;

public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder()
            .UseMauiApp<App>()
            .ConfigureFonts(fonts =>
            {
                fonts.AddFont("Geologica-Regular.ttf", "BielikDisplay");
                fonts.AddFont("Geologica-SemiBold.ttf", "BielikHeading");
                fonts.AddFont("SourceSansPro-Regular.otf", "BielikBody");
                fonts.AddFont("SourceSansPro-Semibold.otf", "BielikBodySemibold");
            });
        builder.Services.AddSingleton(_ => BielikClient.CreateLocalHttpClient());
        builder.Services.AddSingleton<BielikClient>();
        builder.Services.AddSingleton<EssentialsAiInfo>();
        builder.Services.AddSingleton<IPreferences>(Preferences.Default);
        builder.Services.AddSingleton<AppState>();
        builder.Services.AddSingleton<IChatClient>(services => new BielikChatClient(
            services.GetRequiredService<BielikClient>(),
            () => services.GetRequiredService<AppState>().Endpoint));
        builder.Services.AddSingleton<ChatViewModel>();
        builder.Services.AddSingleton<DiscoverPage>();
        builder.Services.AddSingleton<ChatPage>();
        builder.Services.AddSingleton<ModelPage>();
        builder.Services.AddSingleton<SettingsPage>();
        builder.Services.AddSingleton<AppShell>();
        builder.Services.AddSingleton<Func<AppShell>>(services => () => services.GetRequiredService<AppShell>());
#if DEBUG
        builder.Logging.AddDebug();
        var agentPort = 9235;
        var configuredPort = Environment.GetEnvironmentVariable("BIELIK_DEVFLOW_PORT");
        if (configuredPort is not null &&
            (!int.TryParse(configuredPort, NumberStyles.None, CultureInfo.InvariantCulture, out agentPort) ||
             agentPort is < 1 or > 65535))
        {
            throw new InvalidOperationException("BIELIK_DEVFLOW_PORT must be an integer between 1 and 65535.");
        }
        builder.AddMauiDevFlowAgent(options => options.Port = agentPort);
#endif
        return builder.Build();
    }
}
