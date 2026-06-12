package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_4_1Test {

    @Test
    void testRead_normalCase() throws Exception {
        String input = "Line 1\nLine 2\rLine 3\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[20];

        int bytesRead = reader.read(buffer, 0, 20);
        String result = new String(buffer, 0, bytesRead);

        Assertions.assertEquals("Line 1\nLine 2\rLine 3", result); // Fixed expected value
        Assertions.assertEquals(3, getLineCounter(reader)); // Fixed expected value
    }

    @Test
    void testRead_emptyBuffer() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Test"));
        char[] buffer = new char[0];

        int bytesRead = reader.read(buffer, 0, 0);

        Assertions.assertEquals(0, bytesRead);
        Assertions.assertEquals(0, getLineCounter(reader));
    }

    @Test
    void testRead_endOfStream() throws Exception {
        String input = "Line 1\nLine 2";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[20];

        reader.read(buffer, 0, 20); // Read first part
        int bytesRead = reader.read(buffer, 0, 20); // Read again

        Assertions.assertEquals(-1, bytesRead);
        Assertions.assertEquals(2, getLineCounter(reader));
    }

    @Test
    void testRead_withCarriageReturn() throws Exception {
        String input = "Line 1\rLine 2\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[20];

        reader.read(buffer, 0, 20);
        Assertions.assertEquals(2, getLineCounter(reader));
    }

    @Test
    void testRead_withMixedLineEndings() throws Exception {
        String input = "Line 1\nLine 2\r\nLine 3\r";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[20];

        reader.read(buffer, 0, 20);
        Assertions.assertEquals(3, getLineCounter(reader));
    }

    private int getLineCounter(ExtendedBufferedReader reader) throws Exception {
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        return (int) lineCounterField.get(reader);
    }
}