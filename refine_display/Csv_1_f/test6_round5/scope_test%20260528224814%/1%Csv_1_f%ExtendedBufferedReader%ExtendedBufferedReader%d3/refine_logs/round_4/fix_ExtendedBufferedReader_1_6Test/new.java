package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_1_6Test {

    @Test
    void testExtendedBufferedReader_normalCase() throws Exception {
        String input = "Hello World\nThis is a test";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        for (char expected : input.toCharArray()) {
            Assertions.assertEquals(expected, reader.read());
        }
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.read());
    }

    @Test
    void testReadLine() throws Exception {
        String input = "First line\nSecond line";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        String line1 = reader.readLine();
        String line2 = reader.readLine();

        Assertions.assertEquals("First line", line1);
        Assertions.assertEquals("Second line", line2);
    }

    @Test
    void testReadWithBuffer() throws Exception {
        String input = "Buffered read test";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        char[] buffer = new char[10];

        int charsRead = reader.read(buffer, 0, buffer.length);
        Assertions.assertEquals(10, charsRead);
        Assertions.assertEquals("Buffered re", new String(buffer, 0, charsRead));
    }

    @Test
    void testLookAhead() throws Exception {
        String input = "Look ahead test";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        Method lookAheadMethod = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        lookAheadMethod.setAccessible(true);

        int result = (int) lookAheadMethod.invoke(reader);
        Assertions.assertNotEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testGetLineNumber() throws Exception {
        String input = "Line 1\nLine 2";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);

        reader.readLine(); // Read first line
        int lineNumber = (int) getLineNumberMethod.invoke(reader);
        Assertions.assertEquals(1, lineNumber);
    }

    @Test
    void testReadEndOfStream() throws Exception {
        String input = "";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.read());
    }

    @Test
    void testReadThrowsIOException() throws Exception {
        Reader mockReader = Mockito.mock(Reader.class);
        Mockito.when(mockReader.read()).thenThrow(new IOException("Read error"));
        ExtendedBufferedReader reader = new ExtendedBufferedReader(mockReader);

        Assertions.assertThrows(IOException.class, reader::read);
    }
}