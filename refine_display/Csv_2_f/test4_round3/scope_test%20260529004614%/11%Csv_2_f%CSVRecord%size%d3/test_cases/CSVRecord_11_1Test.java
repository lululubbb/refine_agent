package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.lang.reflect.Constructor;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_11_1Test {

    @Test
    public void testSize_emptyArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[0]);
        Assertions.assertEquals(0, record.size());
    }

    @Test
    public void testSize_singleElementArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1"});
        Assertions.assertEquals(1, record.size());
        Assertions.assertEquals("value1", record.get(0));
    }

    @Test
    public void testSize_multipleElementsArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1", "value2", "value3"});
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
    }

    @Test
    public void testSize_boundaryValues() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"", "value2"});
        Assertions.assertEquals(2, record.size());
        Assertions.assertEquals("", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
    }

    @Test
    public void testSize_specialCharacters() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1", "value@2", "value#3"});
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals("value@2", record.get(1));
        Assertions.assertEquals("value#3", record.get(2));
    }

    @Test
    public void testSize_nullArray() throws Exception {
        CSVRecord record = createCSVRecord(null);
        Assertions.assertEquals(0, record.size());
    }

    private CSVRecord createCSVRecord(String[] values) throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 1;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values != null ? values : new String[0], mapping, comment, recordNumber);
    }
}