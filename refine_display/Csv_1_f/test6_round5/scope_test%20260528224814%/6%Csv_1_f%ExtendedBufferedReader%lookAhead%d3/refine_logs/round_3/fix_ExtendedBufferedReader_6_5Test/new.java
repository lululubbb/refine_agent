package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

class ExtendedBufferedReader_6_5Test {

    @Test
    void testLookAhead_normalCase() throws Exception {
        String input = "Hello";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        int result = invokeLookAhead(reader);
        Assertions.assertEquals('H', result);
    }

    @Test
    void testLookAhead_endOfStream() throws Exception {
        String input = "";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        int result = invokeLookAhead(reader);
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testLookAhead_exceptionHandling() throws Exception {
        Reader mockReader = Mockito.mock(Reader.class);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(mockReader);

        Mockito.when(mockReader.read()).thenThrow(new IOException("Read error"));

        Assertions.assertThrows(IOException.class, () -> invokeLookAhead(reader));
    }

    private int invokeLookAhead(ExtendedBufferedReader reader) throws Exception {
        // Using a timeout to avoid excessive execution time
        long startTime = System.currentTimeMillis();
        int result = reader.lookAhead();
        long duration = System.currentTimeMillis() - startTime;

        // Adjusted timeout threshold to ensure it does not exceed the limit
        Assertions.assertTrue(duration < 100, "Execution exceeded timeout limit");
        return result;
    }
}