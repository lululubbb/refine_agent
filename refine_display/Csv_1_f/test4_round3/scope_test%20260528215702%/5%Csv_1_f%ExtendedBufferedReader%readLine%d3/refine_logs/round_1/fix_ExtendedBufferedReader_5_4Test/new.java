package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.StringReader;

class ExtendedBufferedReader_5_4Test {

    @Test
    void testReadLine_normalCase() throws Exception {
        String input = "Hello, World!\nNext line";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        String line = reader.readLine();
        
        Assertions.assertEquals("Hello, World!", line);
        Assertions.assertEquals(1, getLineCounter(reader));
        Assertions.assertEquals('!', getLastChar(reader));
    }

    @Test
    void testReadLine_emptyLine() throws Exception {
        String input = "\nNext line";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        String line = reader.readLine();
        
        Assertions.assertEquals("", line);
        Assertions.assertEquals(1, getLineCounter(reader));
        Assertions.assertEquals('\n', getLastChar(reader));
    }

    @Test
    void testReadLine_endOfStream() throws Exception {
        String input = "Hello, World!";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        reader.readLine(); // Read first line
        String line = reader.readLine(); // Read second line (end of stream)
        
        Assertions.assertNull(line);
        Assertions.assertEquals(1, getLineCounter(reader));
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, getLastChar(reader));
    }

    private int getLineCounter(ExtendedBufferedReader reader) throws Exception {
        return (int) getPrivateField(reader, "lineCounter");
    }

    private int getLastChar(ExtendedBufferedReader reader) throws Exception {
        return (int) getPrivateField(reader, "lastChar");
    }

    private Object getPrivateField(ExtendedBufferedReader reader, String fieldName) throws Exception {
        java.lang.reflect.Field field = ExtendedBufferedReader.class.getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(reader);
    }
}