package org.apache.commons.csv;

import java.util.Arrays;
import java.io.Serializable;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_3_1Test {

    @Test
    public void testGet_withValidHeader_returnsValue() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = invokeGet(record, "header1");

        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_withNullMapping_throwsIllegalStateException() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(values, null, null, 1);

        Exception exception = Assertions.assertThrows(IllegalStateException.class, () -> {
            record.get("header1");
        });

        Assertions.assertEquals("No header mapping was specified, the record values can't be accessed by name", exception.getMessage());
    }

    @Test
    public void testGet_withInvalidHeader_returnsNull() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        String result = invokeGet(record, "header2");

        Assertions.assertNull(result);
    }

    @Test
    public void testGet_withOutOfBoundsIndex_throwsIllegalArgumentException() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 2); // Set index out of bounds
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Exception exception = Assertions.assertThrows(IllegalArgumentException.class, () -> {
            invokeGet(record, "header2"); // This should now throw an exception
        });

        Assertions.assertEquals("Index for header 'header2' is 2 but CSVRecord only has 2 values!", exception.getMessage());
    }

    private String invokeGet(CSVRecord record, String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", String.class);
        method.setAccessible(true);
        return (String) method.invoke(record, name);
    }
}