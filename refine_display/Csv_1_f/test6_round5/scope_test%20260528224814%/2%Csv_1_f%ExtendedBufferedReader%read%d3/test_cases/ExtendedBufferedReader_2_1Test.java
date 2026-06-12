package org.apache.commons.csv;
import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_2_1Test {

    @Test
    void testRead_normalCase() throws Exception {
        String input = "Hello\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        int firstChar = reader.read();
        Assertions.assertEquals('H', firstChar);
        Assertions.assertEquals(0, getLineNumber(reader));

        int secondChar = reader.read();
        Assertions.assertEquals('e', secondChar);
        Assertions.assertEquals(0, getLineNumber(reader));

        // Read until newline
        reader.read(); // 'l'
        reader.read(); // 'l'
        reader.read(); // 'o'
        int newlineChar = reader.read(); // '\n'
        Assertions.assertEquals('\n', newlineChar);
        Assertions.assertEquals(1, getLineNumber(reader));
    }

    @Test
    void testRead_multipleLines() throws Exception {
        String input = "Line 1\nLine 2\nLine 3";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        while (reader.read() != ExtendedBufferedReader.END_OF_STREAM) {
            // Read through the content
        }

        Assertions.assertEquals(2, getLineNumber(reader));
    }

    @Test
    void testRead_endOfStream() throws Exception {
        String input = "Single line";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        while (reader.read() != ExtendedBufferedReader.END_OF_STREAM) {
            // Read through the content
        }

        int endOfStream = reader.read();
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, endOfStream);
    }

    @Test
    void testRead_lineBreaks() throws Exception {
        String input = "First line\rSecond line\nThird line\r\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        while (reader.read() != ExtendedBufferedReader.END_OF_STREAM) {
            // Read through the content
        }

        Assertions.assertEquals(3, getLineNumber(reader));
    }

    private int getLineNumber(ExtendedBufferedReader reader) throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        method.setAccessible(true);
        return (int) method.invoke(reader);
    }
}