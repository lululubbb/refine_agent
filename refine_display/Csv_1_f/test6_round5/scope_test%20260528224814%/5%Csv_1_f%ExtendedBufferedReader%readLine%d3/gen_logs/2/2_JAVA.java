package org.apache.commons.csv;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_5_2Test {

    @Test
    public void testReadLine_normalCase() throws Exception {
        String input = "Hello World\nThis is a test\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line1 = reader.readLine();
        Assertions.assertEquals("Hello World", line1);
        Assertions.assertEquals(1, invokeLineCounter(reader));

        String line2 = reader.readLine();
        Assertions.assertEquals("This is a test", line2);
        Assertions.assertEquals(2, invokeLineCounter(reader));
    }

    @Test
    public void testReadLine_emptyLine() throws Exception {
        String input = "Hello World\n\nThis is a test\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        reader.readLine(); // Read first line
        String emptyLine = reader.readLine(); // Read empty line
        Assertions.assertEquals("", emptyLine);
        Assertions.assertEquals(2, invokeLineCounter(reader));
    }

    @Test
    public void testReadLine_endOfStream() throws Exception {
        String input = "Hello World\nThis is a test\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        reader.readLine(); // Read first line
        reader.readLine(); // Read second line
        String end = reader.readLine(); // Read end of stream
        Assertions.assertNull(end);
        Assertions.assertEquals(2, invokeLineCounter(reader));
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, invokeLastChar(reader));
    }

    @Test
    public void testReadLine_singleCharacter() throws Exception {
        String input = "A\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line = reader.readLine();
        Assertions.assertEquals("A", line);
        Assertions.assertEquals(1, invokeLineCounter(reader));
        Assertions.assertEquals('A', invokeLastChar(reader));
    }

    private int invokeLineCounter(ExtendedBufferedReader reader) throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        method.setAccessible(true);
        return (int) method.invoke(reader);
    }

    private int invokeLastChar(ExtendedBufferedReader reader) throws Exception {
        java.lang.reflect.Field field = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        field.setAccessible(true);
        return (int) field.get(reader);
    }
}