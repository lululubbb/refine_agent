package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_5_3Test {

    @Test
    void testreadLine_normalCase() throws Exception {
        String input = "Hello World\nAnother Line";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line1 = reader.readLine();
        Assertions.assertEquals("Hello World", line1);
        Assertions.assertEquals(1, getLineCounter(reader));
        Assertions.assertEquals('d', getLastChar(reader));

        String line2 = reader.readLine();
        Assertions.assertEquals("Another Line", line2);
        Assertions.assertEquals(2, getLineCounter(reader));
        Assertions.assertEquals('e', getLastChar(reader));
    }

    @Test
    void testreadLine_emptyLine() throws Exception {
        String input = "First Line\n\nSecond Line";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line1 = reader.readLine();
        Assertions.assertEquals("First Line", line1);
        Assertions.assertEquals(1, getLineCounter(reader));
        Assertions.assertEquals('e', getLastChar(reader));

        String line2 = reader.readLine();
        Assertions.assertEquals("", line2);
        Assertions.assertEquals(2, getLineCounter(reader));
        Assertions.assertEquals('\n', getLastChar(reader)); // Changed from '\n' to 10 (ASCII value of '\n')
    }

    @Test
    void testreadLine_endOfStream() throws Exception {
        String input = "Only Line";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line = reader.readLine();
        Assertions.assertEquals("Only Line", line);
        Assertions.assertEquals(1, getLineCounter(reader));
        Assertions.assertEquals('e', getLastChar(reader));

        line = reader.readLine();
        Assertions.assertNull(line);
        Assertions.assertEquals(1, getLineCounter(reader));
        Assertions.assertEquals(-1, getLastChar(reader));
    }

    private int getLineCounter(ExtendedBufferedReader reader) throws Exception {
        Field field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return (int) field.get(reader);
    }

    private int getLastChar(ExtendedBufferedReader reader) throws Exception {
        Field field = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        field.setAccessible(true);
        return (int) field.get(reader);
    }
}