package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_1_1Test {

    @Test
    void testExtendedBufferedReader_read() throws Exception {
        String input = "Hello\nWorld";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        int firstChar = reader.read();
        Assertions.assertEquals('H', firstChar);

        int secondChar = reader.read();
        Assertions.assertEquals('e', secondChar);
    }

    @Test
    void testExtendedBufferedReader_readAgain() throws Exception {
        String input = "Test\n";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);

        // Read the first character to set lastChar
        reader.read();
        int charRead = (int) readAgainMethod.invoke(reader);
        Assertions.assertEquals('T', charRead);
    }

    @Test
    void testExtendedBufferedReader_readWithBuffer() throws Exception {
        String input = "Buffer Test";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        char[] buf = new char[11]; // Updated buffer size to 11

        int charsRead = reader.read(buf, 0, buf.length);
        Assertions.assertEquals(input.length(), charsRead);
        Assertions.assertArrayEquals("Buffer Test".toCharArray(), buf);
    }

    @Test
    void testExtendedBufferedReader_readLine() throws Exception {
        String input = "First Line\nSecond Line";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        String firstLine = reader.readLine();
        Assertions.assertEquals("First Line", firstLine);

        String secondLine = reader.readLine();
        Assertions.assertEquals("Second Line", secondLine);
    }

    @Test
    void testExtendedBufferedReader_lookAhead() throws Exception {
        String input = "Look Ahead";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        Method lookAheadMethod = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        lookAheadMethod.setAccessible(true);

        int lookAheadChar = (int) lookAheadMethod.invoke(reader);
        Assertions.assertEquals('L', lookAheadChar);
    }

    @Test
    void testExtendedBufferedReader_getLineNumber() throws Exception {
        String input = "Line 1\nLine 2";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);

        // Read first line
        reader.readLine();
        int lineNumber = (int) getLineNumberMethod.invoke(reader);
        Assertions.assertEquals(1, lineNumber);
    }
}