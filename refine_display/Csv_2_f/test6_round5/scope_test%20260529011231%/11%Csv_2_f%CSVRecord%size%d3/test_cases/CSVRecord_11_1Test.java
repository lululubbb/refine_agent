package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;

public class CSVRecord_11_1Test {

    @Test
    public void testSize_emptyArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[0], new HashMap<>(), null, 0);
        Assertions.assertEquals(0, record.size());
    }

    @Test
    public void testSize_singleElementArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, new HashMap<>(), null, 1);
        Assertions.assertEquals(1, record.size());
        Assertions.assertEquals("value1", record.get(0));
    }

    @Test
    public void testSize_multipleElementsArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2", "value3"}, new HashMap<>(), null, 2);
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
    }

    @Test
    public void testSize_largeArray() throws Exception {
        String[] values = new String[1000];
        Arrays.fill(values, "value");
        CSVRecord record = new CSVRecord(values, new HashMap<>(), null, 3);
        Assertions.assertEquals(1000, record.size());
        for (int i = 0; i < 1000; i++) {
            Assertions.assertEquals("value", record.get(i));
        }
    }

    @Test
    public void testSize_withNullValues() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{null, null}, new HashMap<>(), null, 4);
        Assertions.assertEquals(2, record.size());
        Assertions.assertNull(record.get(0));
        Assertions.assertNull(record.get(1));
    }

    @Test
    public void testSize_boundaryValues() throws Exception {
        CSVRecord record = new CSVRecord(new String[1000], new HashMap<>(), null, 5);
        Assertions.assertEquals(1000, record.size());

        CSVRecord recordWithOneLess = new CSVRecord(new String[999], new HashMap<>(), null, 6);
        Assertions.assertEquals(999, recordWithOneLess.size());

        // Additional boundary tests
        CSVRecord recordWithOneElement = new CSVRecord(new String[]{"single"}, new HashMap<>(), null, 7);
        Assertions.assertEquals(1, recordWithOneElement.size());
        Assertions.assertEquals("single", recordWithOneElement.get(0));

        CSVRecord recordWithEmptyString = new CSVRecord(new String[]{""}, new HashMap<>(), null, 8);
        Assertions.assertEquals(1, recordWithEmptyString.size());
        Assertions.assertEquals("", recordWithEmptyString.get(0));
    }

    private void setPrivateField(CSVRecord record, String fieldName, Object value) throws Exception {
        Field field = CSVRecord.class.getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(record, value);
    }
}