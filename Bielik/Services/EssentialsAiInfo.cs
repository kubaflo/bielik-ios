#if IOS
using Bielik.Core;
using Microsoft.Extensions.AI;
using Microsoft.Maui.Essentials.AI;
#endif

namespace Bielik.Services;

public sealed class EssentialsAiInfo
{
    public string Description { get; } = DescribeProvider();

    private static string DescribeProvider()
    {
#if IOS
        if (!OperatingSystem.IsIOSVersionAtLeast(26))
        {
            return "Microsoft.Maui.Essentials.AI wymaga iOS 26+ dla Apple Intelligence. Rozmowę nadal obsługuje lokalny Bielik.";
        }

#pragma warning disable MAUIAI0001
        using IChatClient nativeClient = new AppleIntelligenceChatClient();
#pragma warning restore MAUIAI0001
        var metadata = nativeClient.GetService<ChatClientMetadata>()
            ?? throw new InvalidOperationException("Essentials AI nie zwróciło metadanych dostawcy.");
        if (metadata.DefaultModelId == ModelInfo.Id)
        {
            throw new InvalidOperationException("Nieoczekiwana zmiana modelu systemowego Essentials AI.");
        }

        return $"Essentials AI udostępnia dostawcę {metadata.ProviderName} / {metadata.DefaultModelId}. To inny model niż Bielik, więc nie używamy go do rozmowy. Gotowość jego wag nie jest sprawdzana.";
#else
        return "Microsoft.Maui.Essentials.AI nie ma jeszcze natywnego dostawcy dla Androida. IChatClient obsługuje tutaj wyłącznie lokalnego Bielika na Twoim Macu.";
#endif
    }
}
