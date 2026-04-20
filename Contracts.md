# Contracts of interaction

## UIBot
```text
-> FulfillmentService        get  /api/get_all_channel
-> FulfillmentService        get  /api/get_channel/{channel_id}
-> FulfillmentService        post /api/get_channel/filter // в теле инфа по которой должны найтись каналы
-> FulfillmentService        post /api/book_channel/{channel_id}
-> FulfillmentService        post /api/change_owner/{channel_id}
-> FulfillmentService        post /api/create_channel // в теле параметры создания
```

## Content-Scheduler Service
```text
post /api/add_account_schedule/{account_id} // добавляем аккаунт для планирования + в теле настройки планирования
```

## PostingService
```text
post /api/post_msg/
post /api/change_msg/{msg_id}
```

## ChannelService
```text
post /api/create_channel
get  /api/get_channel_info
post /api/change_owner/{channel_id}
-> TgAdapterChannelService post /api/change_owner/{channel_id}
```

## TgAdapterPostingService
```text
post /api/post_msg/
post /api/change_msg/{msg_id}
get  /api/get_channel_info
```

## TgAdapterChannelService
```text
post /api/create_tg_channel
get  /api/get_tg_channel_info
get  /api/get_tg_channel_statistic
post /api/change_owner/{channel_id}
```

## FulfillmentService
```text
get  /api/get_all_channel
get  /api/get_channel/{channel_id}
post /api/get_channel/filter // в теле инфа по которой должны фильтроваться каналы

post /api/book_channel/{channel_id}

post /api/change_owner/{channel_id}
-> ChannelService post /api/change_owner/{channel_id}

post /api/create_channel
-> Content-Scheduler Service post /api/add_account_schedule/{account_id} // опционально
-> ChannelService             post /api/create_channel
```
