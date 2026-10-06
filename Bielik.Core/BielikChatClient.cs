using System.Runtime.CompilerServices;
using Microsoft.Extensions.AI;
using AIChatMessage = Microsoft.Extensions.AI.ChatMessage;
using AIChatOptions = Microsoft.Extensions.AI.ChatOptions;

namespace Bielik.Core;

public sealed class BielikChatClient : IChatClient
{
    public const string MetricsProperty = "bielik.generation_metrics";
    private readonly BielikClient _client;
    private readonly Func<LocalEndpoint> _getEndpoint;
    private readonly ChatClientMetadata _metadata = new("ollama", defaultModelId: ModelInfo.Id);
    private int _disposed;

    public BielikChatClient(BielikClient client, Func<LocalEndpoint> getEndpoint)
    {
        ArgumentNullException.ThrowIfNull(client);
        ArgumentNullException.ThrowIfNull(getEndpoint);
        _client = client;
        _getEndpoint = getEndpoint;
    }

    public async Task<ChatResponse> GetResponseAsync(
        IEnumerable<AIChatMessage> messages,
        AIChatOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        GenerationMetrics? metrics = null;
        async IAsyncEnumerable<ChatResponseUpdate> CaptureMetricsAsync()
        {
            await foreach (var update in GetStreamingResponseAsync(messages, options, cancellationToken))
            {
                if (update.RawRepresentation is ChatChunk { Metrics: { } generationMetrics })
                {
                    metrics = generationMetrics;
                }

                yield return update;
            }
        }

        var response = await CaptureMetricsAsync().ToChatResponseAsync(cancellationToken);
        if (metrics is not null)
        {
            // MEAI aggregation does not promote update metadata to response metadata.
            (response.AdditionalProperties ??= new())[MetricsProperty] = metrics;
        }

        return response;
    }

    public async IAsyncEnumerable<ChatResponseUpdate> GetStreamingResponseAsync(
        IEnumerable<AIChatMessage> messages,
        AIChatOptions? options = null,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        ObjectDisposedException.ThrowIf(Volatile.Read(ref _disposed) != 0, this);
        ArgumentNullException.ThrowIfNull(messages);
        cancellationToken.ThrowIfCancellationRequested();
        ValidateOptions(options);
        var conversation = messages.Select(ToConversationMessage).ToArray();
        var endpoint = _getEndpoint();
        var responseId = Guid.NewGuid().ToString("N");
        var createdAt = DateTimeOffset.UtcNow;

        await foreach (var chunk in _client.StreamAsync(endpoint, conversation, cancellationToken))
        {
            var update = new ChatResponseUpdate(ChatRole.Assistant, chunk.Text)
            {
                ModelId = ModelInfo.Id,
                ResponseId = responseId,
                MessageId = responseId,
                CreatedAt = createdAt,
                RawRepresentation = chunk
            };
            if (chunk.IsComplete)
            {
                update.FinishReason = new ChatFinishReason(
                    string.IsNullOrWhiteSpace(chunk.FinishReason) ? "complete" : chunk.FinishReason);
                if (chunk.Metrics is { } metrics)
                {
                    update.Contents.Add(new UsageContent(new UsageDetails
                    {
                        InputTokenCount = metrics.InputTokens,
                        OutputTokenCount = metrics.Tokens,
                        TotalTokenCount = metrics.InputTokens is { } inputTokens ? (long)inputTokens + metrics.Tokens : null
                    }));
                    update.AdditionalProperties = new() { [MetricsProperty] = metrics };
                }
            }

            yield return update;
        }

        cancellationToken.ThrowIfCancellationRequested();
    }

    public object? GetService(Type serviceType, object? serviceKey = null)
    {
        ObjectDisposedException.ThrowIf(Volatile.Read(ref _disposed) != 0, this);
        ArgumentNullException.ThrowIfNull(serviceType);
        if (serviceKey is not null)
        {
            return null;
        }

        if (serviceType == typeof(ChatClientMetadata))
        {
            return _metadata;
        }

        if (serviceType.IsInstanceOfType(this))
        {
            return this;
        }

        return serviceType.IsInstanceOfType(_client) ? _client : null;
    }

    public void Dispose() => Interlocked.Exchange(ref _disposed, 1);

    private static ChatMessage ToConversationMessage(AIChatMessage message)
    {
        ArgumentNullException.ThrowIfNull(message);
        if (message.Contents.Any(content => content is not TextContent))
        {
            throw new NotSupportedException("Ten Bielik obsługuje tylko wiadomości tekstowe, bez obrazów i wywołań narzędzi.");
        }

        if (message.Role != ChatRole.User && message.Role != ChatRole.Assistant)
        {
            throw new ArgumentException("Instrukcja systemowa Bielika jest przypięta. Dozwolone są tylko role user i assistant.", nameof(message));
        }

        return new ChatMessage(message.Role.Value, message.Text);
    }

    private static void ValidateOptions(AIChatOptions? options)
    {
        if (options is null)
        {
            return;
        }

        if (options.ModelId is { } modelId && !string.Equals(modelId, ModelInfo.Id, StringComparison.OrdinalIgnoreCase))
        {
            throw new ArgumentException("Dozwolony jest wyłącznie przypięty lokalny Bielik.", nameof(options));
        }

#pragma warning disable MEAI001 // Inspect experimental options only to reject unsupported background requests.
        var requestsBackgroundResponse = options.AllowBackgroundResponses is not null || options.ContinuationToken is not null;
#pragma warning restore MEAI001
        if (options.Instructions is not null || options.ConversationId is not null ||
            options.Temperature is not null || options.MaxOutputTokens is not null ||
            options.TopP is not null || options.TopK is not null ||
            options.FrequencyPenalty is not null || options.PresencePenalty is not null ||
            options.Seed is not null || options.Reasoning is not null ||
            options.ResponseFormat is not null || options.StopSequences is { Count: > 0 } ||
            options.AllowMultipleToolCalls is not null || options.ToolMode is not null ||
            options.Tools is { Count: > 0 } || requestsBackgroundResponse ||
            options.RawRepresentationFactory is not null ||
            options.AdditionalProperties is { Count: > 0 })
        {
            throw new NotSupportedException(
                "Ten klient korzysta z przypiętej konfiguracji Bielika: CPU, 8192 tokenów kontekstu, temperatura 0,1 i maksymalnie 768 tokenów odpowiedzi.");
        }
    }
}
