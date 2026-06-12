package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_6_1Test {

    @Test
    void testLookAhead_normalCase() throws Exception {
        String input = "Hello";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        // Avoid timeout by ensuring lookAhead method is called correctly
        int result = reader.lookAhead();
        Assertions.assertEquals('H', result);
    }

    @Test
    void testLookAhead_endOfStream() throws Exception {
        String input = "";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        // Avoid timeout by ensuring lookAhead method is called correctly
        int result = reader.lookAhead();
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testLookAhead_exceptionHandling() throws Exception {
        Reader mockReader = Mockito.mock(Reader.class);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(mockReader);

        Mockito.when(mockReader.read()).thenThrow(new IOException("Test Exception"));

        Assertions.assertThrows(IOException.class, () -> {
            // Avoid timeout by ensuring lookAhead method is called correctly
            reader.lookAhead();
        });
    }
}