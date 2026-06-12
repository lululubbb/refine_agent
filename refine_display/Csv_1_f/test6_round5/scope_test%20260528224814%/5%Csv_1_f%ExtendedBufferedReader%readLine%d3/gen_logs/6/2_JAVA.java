package org.apache.commons.csv;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.StringReader;

class ExtendedBufferedReader_5_6Test {
    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        reader = new ExtendedBufferedReader(new StringReader(""));
    }

    @Test
    void testReadLine_normalCase() throws Exception {
        reader = new ExtendedBufferedReader(new StringReader("Hello World\nNext Line"));
        String line = reader.readLine();
        Assertions.assertEquals("Hello World", line);
        Assertions.assertEquals(1, getLineCounter(reader));
        Assertions.assertEquals('d', getLastChar(reader));
    }

    @Test
    void testReadLine_emptyLine() throws Exception {
        reader = new ExtendedBufferedReader(new StringReader("\nNext Line"));
        String line = reader.readLine();
        Assertions.assertEquals("", line);
        Assertions.assertEquals(1, getLineCounter(reader));
        Assertions.assertEquals(' ', getLastChar(reader));
    }

    @Test
    void testReadLine_endOfStream() throws Exception {
        reader = new ExtendedBufferedReader(new StringReader(""));
        String line = reader.readLine();
        Assertions.assertNull(line);
        Assertions.assertEquals(0, getLineCounter(reader));
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, getLastChar(reader));
    }

    @Test
    void testReadLine_multipleLines() throws Exception {
        reader = new ExtendedBufferedReader(new StringReader("First Line\nSecond Line\n"));
        String line1 = reader.readLine();
        String line2 = reader.readLine();
        Assertions.assertEquals("First Line", line1);
        Assertions.assertEquals("Second Line", line2);
        Assertions.assertEquals(2, getLineCounter(reader));
        Assertions.assertEquals('e', getLastChar(reader));
    }

    private int getLineCounter(ExtendedBufferedReader reader) throws Exception {
        var field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return field.getInt(reader);
    }

    private int getLastChar(ExtendedBufferedReader reader) throws Exception {
        var field = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        field.setAccessible(true);
        return field.getInt(reader);
    }
}