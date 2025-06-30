using System;
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Azure.Storage.Queues;
using Azure.Storage.Queues.Models;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;

namespace Company.Function;

public class QueueTrigger1
{
    private readonly ILogger<QueueTrigger1> _logger;

    public QueueTrigger1(ILogger<QueueTrigger1> logger)
    {
        _logger = logger;
    }

    [Function(nameof(QueueTrigger1))]
    public async Task Run([QueueTrigger("input", Connection = "AzureWebJobsStorage")] QueueMessage message)
    {
        _logger.LogInformation("C# Queue trigger function processed: {messageText}", message.MessageText);
        
        try
        {
            // Parse the input JSON message
            var inputMessage = JsonSerializer.Deserialize<InputMessage>(message.MessageText);
            
            if (inputMessage == null)
            {
                _logger.LogWarning("Failed to deserialize message or message is null");
                return;
            }
            
            _logger.LogInformation("Parsed message - DNI: {customer_id}, CorrelationId: {correlationId}", 
                inputMessage.customer_id, inputMessage.CorrelationId);
            //obtengo de redis el token de usuario con llave customer_id
            var responseMessage = new ResponseMessage
            {
                CorrelationId = inputMessage.CorrelationId,
                Value = $"{{\"customer_id\":\"{inputMessage.customer_id}\", \"status\":\"failed\", \"message\":\"Processed failed, contact customer support\"}}"
            };

            // Send to output queue
            var connectionString = Environment.GetEnvironmentVariable("AzureWebJobsStorage");
            var queueClient = new QueueClient(connectionString, "output");
            await queueClient.CreateIfNotExistsAsync();
            
            var responseJson = JsonSerializer.Serialize(responseMessage);
            
            // Base64 encode the message before sending to queue
            var messageBytes = Encoding.UTF8.GetBytes(responseJson);
            var base64Message = Convert.ToBase64String(messageBytes);
            
            await queueClient.SendMessageAsync(base64Message);
            
            _logger.LogInformation("Response sent to output queue (Base64 encoded): {response}", responseJson);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing queue message");
            throw;
        }
    }
}

public class InputMessage
{
    public string customer_id { get; set; }
    public string CorrelationId { get; set; }
}

public class ResponseMessage
{
    public string CorrelationId { get; set; }
    public string Value { get; set; }
}