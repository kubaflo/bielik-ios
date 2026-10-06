using System.Net;
using System.Text;
using System.Text.Json;
using Bielik.Core;
using Microsoft.Extensions.AI;
using Xunit;
using AIChatMessage = Microsoft.Extensions.AI.ChatMessage;

namespace Bielik.Core.Tests;

public sealed class BielikChatClientTests
{
    [Fact]
    public async Task StreamsMeaiTextCompletionAndUsageThroughThePinnedTransport()
    {
        using var fixture = new Fixture(Frame("Cześć") + "\n" + Frame(" świecie!", true));
        var updates = await CollectAsync(fixture.Client, [new(ChatRole.User, "Powitaj mnie.")]);

        Assert.Equal("Cześć świecie!", string.Concat(updates.Select(update => update.Text)));
        Assert.All(updates, update =>
        {
            Assert.Equal(ChatRole.Assistant, update.Role);
            Assert.Equal(ModelInfo.Id, update.ModelId);
            Assert.Equal(updates[0].ResponseId, update.ResponseId);
            Assert.Equal(update.ResponseId, update.MessageId);
            Assert.NotNull(update.CreatedAt);
        });
        Assert.Null(updates[0].FinishReason);
        Assert.Equal(ChatFinishReason.Stop, updates[^1].FinishReason);
        var usage = Assert.Single(updates[^1].Contents.OfType<UsageContent>()).Details;
        Assert.Equal(18, usage.InputTokenCount);
        Assert.Equal(50, usage.OutputTokenCount);
        Assert.Equal(68, usage.TotalTokenCount);
        var metrics = Assert.IsType<GenerationMetrics>(updates[^1].AdditionalProperties![BielikChatClient.MetricsProperty]);
        Assert.Equal(25, metrics.TokensPerSecond);
        using var request = JsonDocument.Parse(fixture.Handler.LastBody!);
        Assert.Equal(ModelInfo.Id, request.RootElement.GetProperty("model").GetString());
        Assert.Equal(0, request.RootElement.GetProperty("options").GetProperty("num_gpu").GetInt32());
        Assert.Equal(ModelInfo.SystemPrompt, request.RootElement.GetProperty("messages")[0].GetProperty("content").GetString());
    }

    [Fact]
    public async Task AggregatesAStandardMeaiResponseIncludingUsageAndMetrics()
    {
        using var fixture = new Fixture(Frame("Odpowiedź") + "\n" + Frame(" lokalna.", true));
        var response = await fixture.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")]);

        Assert.Equal("Odpowiedź lokalna.", response.Text);
        Assert.Equal(ChatRole.Assistant, Assert.Single(response.Messages).Role);
        Assert.Equal(ModelInfo.Id, response.ModelId);
        Assert.Equal(ChatFinishReason.Stop, response.FinishReason);
        Assert.Equal(68, response.Usage!.TotalTokenCount);
        Assert.IsType<GenerationMetrics>(response.AdditionalProperties![BielikChatClient.MetricsProperty]);
        Assert.NotNull(response.ResponseId);
    }

    [Theory]
    [InlineData("stop", "stop")]
    [InlineData("length", "length")]
    [InlineData(null, "complete")]
    public async Task PreservesTheReportedFinishReasonWithoutInventingAStop(string? reported, string expected)
    {
        using var fixture = new Fixture(Frame("Gotowe.", true, finishReason: reported));
        var response = await fixture.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")]);
        Assert.Equal(expected, response.FinishReason!.Value.Value);
    }

    [Fact]
    public async Task DoesNotInventMissingInputUsage()
    {
        using var fixture = new Fixture(Frame("Gotowe.", true, inputTokens: null));
        var response = await fixture.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")]);
        Assert.Null(response.Usage!.InputTokenCount);
        Assert.Null(response.Usage.TotalTokenCount);
        Assert.Equal(50, response.Usage.OutputTokenCount);
    }

    [Fact]
    public async Task AcceptsOnlyThePinnedModelOption()
    {
        using var fixture = new Fixture(Frame("Tak.", true));
        var response = await fixture.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")],
            new ChatOptions { ModelId = ModelInfo.Id });
        Assert.Equal("Tak.", response.Text);
        await Assert.ThrowsAsync<ArgumentException>(() => fixture.Client.GetResponseAsync(
            [new(ChatRole.User, "Pytanie")], new ChatOptions { ModelId = "different-model" }));
        Assert.Single(fixture.Handler.Addresses);
    }

    [Fact]
    public async Task RejectsUnsupportedOptionsBeforeSendingAnyRequest()
    {
        ChatOptions[] unsupported =
        [
            new() { Instructions = "Override" },
            new() { ConversationId = "server-state" },
            new() { Temperature = 0.8f },
            new() { MaxOutputTokens = 2048 },
            new() { TopP = 0.5f },
            new() { TopK = 2 },
            new() { FrequencyPenalty = 1 },
            new() { PresencePenalty = 1 },
            new() { Seed = 7 },
            new() { ResponseFormat = ChatResponseFormat.Json },
            new() { StopSequences = ["override"] },
            new() { AllowMultipleToolCalls = true },
            new() { ToolMode = ChatToolMode.Auto },
            new() { RawRepresentationFactory = _ => new object() },
            new() { AdditionalProperties = new() { ["endpoint"] = "https://example.com" } }
        ];
        using var fixture = new Fixture(Frame("Nie.", true));
        foreach (var options in unsupported)
        {
            await Assert.ThrowsAsync<NotSupportedException>(() =>
                fixture.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")], options));
        }

        Assert.Empty(fixture.Handler.Addresses);
    }

    [Fact]
    public async Task RejectsExperimentalBackgroundOptionsRatherThanIgnoringThem()
    {
#pragma warning disable MEAI001
        ChatOptions[] unsupported =
        [
            new() { AllowBackgroundResponses = true },
            new() { ContinuationToken = ResponseContinuationToken.FromBytes(Encoding.UTF8.GetBytes("resume-other-state")) }
        ];
#pragma warning restore MEAI001
        using var fixture = new Fixture(Frame("Nie.", true));
        foreach (var options in unsupported)
        {
            await Assert.ThrowsAsync<NotSupportedException>(() =>
                fixture.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")], options));
        }

        Assert.Empty(fixture.Handler.Addresses);
    }

    [Fact]
    public async Task RejectsImagesAndToolCallsBeforeSendingAnyRequest()
    {
        AIContent[] unsupported =
        [
            new DataContent(new byte[] { 1, 2 }, "image/png"),
            new FunctionCallContent("call-id", "tool", new Dictionary<string, object?>())
        ];
        using var fixture = new Fixture(Frame("Nie.", true));
        foreach (var content in unsupported)
        {
            await Assert.ThrowsAsync<NotSupportedException>(() =>
                fixture.Client.GetResponseAsync([new AIChatMessage(ChatRole.User, [content])]));
        }

        Assert.Empty(fixture.Handler.Addresses);
    }

    [Fact]
    public async Task CombinesTextPartsWithoutLosingConversationTurns()
    {
        using var fixture = new Fixture(Frame("Tak.", true));
        await fixture.Client.GetResponseAsync(
        [
            new(ChatRole.User, [new TextContent("Pierwsze "), new TextContent("pytanie")]),
            new(ChatRole.Assistant, "Pierwsza odpowiedź"),
            new(ChatRole.User, "Drugie pytanie")
        ]);
        using var request = JsonDocument.Parse(fixture.Handler.LastBody!);
        var messages = request.RootElement.GetProperty("messages");
        Assert.Equal(4, messages.GetArrayLength());
        Assert.Equal("Pierwsze pytanie", messages[1].GetProperty("content").GetString());
        Assert.Equal("assistant", messages[2].GetProperty("role").GetString());
        Assert.Equal("Drugie pytanie", messages[3].GetProperty("content").GetString());
    }

    [Theory]
    [InlineData("system")]
    [InlineData("tool")]
    [InlineData("developer")]
    public async Task RejectsUnsupportedRoles(string role)
    {
        using var fixture = new Fixture(Frame("Nie.", true));
        await Assert.ThrowsAsync<ArgumentException>(() =>
            fixture.Client.GetResponseAsync([new(new ChatRole(role), "Override")]));
        Assert.Empty(fixture.Handler.Addresses);
    }

    [Fact]
    public async Task PreservesWholeTurnHistoryLimits()
    {
        using var fixture = new Fixture(Frame("Tak.", true));
        var messages = Enumerable.Range(0, 15)
            .Select(index => new AIChatMessage(index % 2 == 0 ? ChatRole.User : ChatRole.Assistant, $"Wiadomość {index}"));
        await fixture.Client.GetResponseAsync(messages);
        using var request = JsonDocument.Parse(fixture.Handler.LastBody!);
        var sent = request.RootElement.GetProperty("messages");
        Assert.Equal(12, sent.GetArrayLength());
        Assert.Equal("user", sent[1].GetProperty("role").GetString());
        Assert.Equal("Wiadomość 4", sent[1].GetProperty("content").GetString());
        Assert.Equal("Wiadomość 14", sent[11].GetProperty("content").GetString());
    }

    [Fact]
    public async Task PreservesValidationOfEmptyAndIncompleteTurns()
    {
        using var fixture = new Fixture(Frame("Nie.", true));
        await Assert.ThrowsAsync<ArgumentException>(() => fixture.Client.GetResponseAsync([]));
        await Assert.ThrowsAsync<ArgumentException>(() => fixture.Client.GetResponseAsync([new(ChatRole.User, " ")]));
        await Assert.ThrowsAsync<ArgumentException>(() => fixture.Client.GetResponseAsync(
            [new(ChatRole.User, "Pytanie"), new(ChatRole.Assistant, "Odpowiedź")]));
        Assert.Empty(fixture.Handler.Addresses);
    }

    [Fact]
    public async Task ResolvesTheCurrentEndpointForEachConversation()
    {
        var endpoint = LocalEndpoint.Parse(ModelInfo.DefaultEndpoint);
        using var fixture = new Fixture(Frame("Tak.", true), () => endpoint);
        await fixture.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")]);
        endpoint = LocalEndpoint.Parse(ModelInfo.AndroidEmulatorEndpoint);
        await fixture.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")]);
        Assert.Equal(
            [new Uri("http://127.0.0.1:11434/api/chat"), new Uri("http://10.0.2.2:11434/api/chat")],
            fixture.Handler.Addresses);
    }

    [Fact]
    public async Task PropagatesTruncatedMalformedAndWrongModelResponses()
    {
        using var truncated = new Fixture(Frame("Fragment"));
        await Assert.ThrowsAsync<EndOfStreamException>(() => truncated.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")]));
        using var malformed = new Fixture("{broken");
        await Assert.ThrowsAsync<JsonException>(() => malformed.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")]));
        using var otherModel = new Fixture(Frame("Nie.", true).Replace(ModelInfo.Id, "different-model"));
        await Assert.ThrowsAsync<InvalidDataException>(() => otherModel.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")]));
        using var empty = new Fixture(Frame("", true));
        await Assert.ThrowsAsync<InvalidDataException>(() => empty.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")]));
        using var serverError = new Fixture("""{"error":"model not loaded"}""");
        await Assert.ThrowsAsync<InvalidOperationException>(() => serverError.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")]));
    }

    [Fact]
    public async Task CancelsBeforeSendingAnyRequest()
    {
        using var fixture = new Fixture(Frame("Nie.", true));
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            fixture.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")], cancellationToken: cancellation.Token));
        Assert.Empty(fixture.Handler.Addresses);
    }

    [Fact]
    public async Task CancelsAnInFlightStreamAndDisposesItsResponse()
    {
        using var stream = new BlockingStream(Encoding.UTF8.GetBytes(Frame("Fragment") + "\n"));
        using var handler = new Handler(() => new StreamContent(stream));
        using var http = new HttpClient(handler);
        using var client = new BielikChatClient(new BielikClient(http), () => LocalEndpoint.Parse(ModelInfo.DefaultEndpoint));
        using var cancellation = new CancellationTokenSource();
        await using var updates = client.GetStreamingResponseAsync(
            [new(ChatRole.User, "Pytanie")], cancellationToken: cancellation.Token).GetAsyncEnumerator();
        Assert.True(await updates.MoveNextAsync());
        Assert.Equal("Fragment", updates.Current.Text);
        cancellation.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => updates.MoveNextAsync().AsTask());
        Assert.True(stream.IsDisposed);
    }

    [Fact]
    public async Task DisposingTheProviderDoesNotDisposeTheInjectedHttpClient()
    {
        using var fixture = new Fixture(Frame("Tak.", true));
        fixture.Client.Dispose();
        await Assert.ThrowsAsync<ObjectDisposedException>(() => fixture.Client.GetResponseAsync([new(ChatRole.User, "Pytanie")]));
        await fixture.Http.GetAsync("http://127.0.0.1:11434/api/tags");
        Assert.Single(fixture.Handler.Addresses);
    }

    [Fact]
    public void ExposesHonestProviderMetadataAndUnkeyedServices()
    {
        using var fixture = new Fixture(Frame("Tak.", true));
        var metadata = Assert.IsType<ChatClientMetadata>(fixture.Client.GetService(typeof(ChatClientMetadata)));
        Assert.Equal("ollama", metadata.ProviderName);
        Assert.Equal(ModelInfo.Id, metadata.DefaultModelId);
        Assert.Null(metadata.ProviderUri);
        Assert.Same(fixture.Client, fixture.Client.GetService(typeof(IChatClient)));
        Assert.Same(fixture.Transport, fixture.Client.GetService(typeof(BielikClient)));
        Assert.Null(fixture.Client.GetService(typeof(IChatClient), "apple"));
        Assert.Null(fixture.Client.GetService(typeof(string)));
    }

    private static string Frame(string text, bool done = false, int? inputTokens = 18, string? finishReason = "stop") =>
        JsonSerializer.Serialize(new
        {
            model = ModelInfo.Id,
            message = new { role = "assistant", content = text },
            done,
            eval_count = 50,
            eval_duration = 2_000_000_000L,
            prompt_eval_count = inputTokens,
            done_reason = finishReason
        });

    private static async Task<List<ChatResponseUpdate>> CollectAsync(IChatClient client, IEnumerable<AIChatMessage> messages)
    {
        var result = new List<ChatResponseUpdate>();
        await foreach (var update in client.GetStreamingResponseAsync(messages))
        {
            result.Add(update);
        }

        return result;
    }

    private sealed class Fixture : IDisposable
    {
        public Fixture(string body, Func<LocalEndpoint>? getEndpoint = null)
        {
            Handler = new Handler(() => new StringContent(body, Encoding.UTF8, "application/x-ndjson"));
            Http = new HttpClient(Handler);
            Transport = new BielikClient(Http);
            Client = new BielikChatClient(Transport, getEndpoint ?? (() => LocalEndpoint.Parse(ModelInfo.DefaultEndpoint)));
        }

        public Handler Handler { get; }
        public HttpClient Http { get; }
        public BielikClient Transport { get; }
        public BielikChatClient Client { get; }

        public void Dispose()
        {
            Client.Dispose();
            Http.Dispose();
        }
    }

    private sealed class Handler(Func<HttpContent> createContent) : HttpMessageHandler
    {
        public List<Uri> Addresses { get; } = [];
        public string? LastBody { get; private set; }

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            Addresses.Add(request.RequestUri!);
            LastBody = request.Content is null ? null : await request.Content.ReadAsStringAsync(cancellationToken);
            return new HttpResponseMessage(HttpStatusCode.OK) { Content = createContent() };
        }
    }

    private sealed class BlockingStream(byte[] prefix) : Stream
    {
        private int _position;
        public bool IsDisposed { get; private set; }
        public override bool CanRead => true;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException();
        public override long Position { get => _position; set => throw new NotSupportedException(); }
        public override void Flush() => throw new NotSupportedException();
        public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();

        public override async ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
        {
            if (_position == prefix.Length)
            {
                await Task.Delay(Timeout.Infinite, cancellationToken);
            }

            var count = Math.Min(buffer.Length, prefix.Length - _position);
            prefix.AsMemory(_position, count).CopyTo(buffer);
            _position += count;
            return count;
        }

        protected override void Dispose(bool disposing)
        {
            IsDisposed = true;
            base.Dispose(disposing);
        }
    }
}
