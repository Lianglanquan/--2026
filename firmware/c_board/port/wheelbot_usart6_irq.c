#include "main.h"

/* USART6 is the C Board connector marked USART1 (PG14/PG9).  FashionStar's
 * official HAL SDK receives one byte at a time through HAL's callback path. */
void USART6_IRQHandler(void)
{
    extern UART_HandleTypeDef huart6;
    HAL_UART_IRQHandler(&huart6);
}
