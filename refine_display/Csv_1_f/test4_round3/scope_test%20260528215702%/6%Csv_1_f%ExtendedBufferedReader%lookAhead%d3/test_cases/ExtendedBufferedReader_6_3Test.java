package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_6_3Test {

    @Test
    void testLookAhead_normalCase() throws Exception {
        String input = "Hello";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        // Directly call lookAhead to avoid timeout in reflection
        int result = reader.lookAhead();

        Assertions.assertEquals('H', result);
    }

    @Test
    void testLookAhead_endOfStream() throws Exception {
        String input = "";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        // Directly call lookAhead to avoid timeout in reflection
        int result = reader.lookAhead();

        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testLookAhead_exceptionHandling() throws Exception {
        Reader mockReader = Mockito.mock(Reader.class);
        Mockito.when(mockReader.read()).thenThrow(new IOException("Mocked IOException"));
        ExtendedBufferedReader reader = new ExtendedBufferedReader(mockReader);

        Assertions.assertThrows(IOException.class, () -> {
            // Directly call lookAhead to avoid timeout in reflection
            reader.lookAhead();
        });
    }
}