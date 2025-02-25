namespace VKTaskBot.Config
{
    public class BotConfig
    {
        public string AccessToken { get; set; }
        public int ReconnectDelay { get; set; }
        public int MaxReconnectAttempts { get; set; }
        public int DeadlineCheckInterval { get; set; }
        public int DeadlineWarningThreshold { get; set; }
    }
}
